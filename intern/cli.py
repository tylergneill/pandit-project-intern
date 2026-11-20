"""The command line: python -m intern <command> ...

    status                      what's open, blocked, waiting on Tyler or others
    intake [NOTES | --latest]   add review tasks from a SETI research-notes report
    next [-n 5] [--batch B]     the next tasks to do, in dependency order
    show T0001 [T0002 ...]      every field of some tasks
    add --action ... --summary  add a change task (usually while reviewing a finding)
    set T0001 STATUS            record progress: filled, saved, filed, done, dropped
    seti-updates [--mark T..]   saved records whose IDs still need to go into the SETI master
    awaiting-export             Pandit IDs saved since the last re-export
    reconcile [--extract CSV]   after a re-export: mark saved tasks done if it shows them

SETI is looked for at ../seti (beside this repo), or wherever SETI_DIR or
--seti says.
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from intern import intake as intake_mod
from intern import pandit as pandit_mod
from intern.todo import ACTIONS, OPEN, ROOT, ROUTES, STATUSES, TODO, TodoError, TodoList, today


def seti_dir(args):
    return Path(args.seti or os.environ.get("SETI_DIR") or ROOT.parent / "seti")


def line(row):
    """One task on one line, for lists."""
    extra = f" -> {row['Pandit ID']}" if row["Pandit ID"] else ""
    target = f" [{row['Target']}]" if row["Target"] else ""
    return f"{row['ID']} {row['Status']:<7} {row['Action']:<14}{target} {row['Summary']}{extra}"


def wrap(label, text):
    return textwrap.fill(text, width=100, initial_indent=f"  {label:<12} ", subsequent_indent=" " * 15)


# ---------- commands ----------

def cmd_status(todo, args):
    counts = {s: 0 for s in STATUSES}
    for r in todo.rows:
        counts[r["Status"]] += 1
    print(f"{len(todo.rows)} tasks in {todo.path.relative_to(ROOT) if todo.path.is_relative_to(ROOT) else todo.path}")
    for s, n in counts.items():
        if n:
            print(f"  {n:>4} {s:<8} {STATUSES[s]}")
    remaining = sum(counts[s] for s in OPEN)
    reviews = sum(1 for r in todo.rows if r["Status"] in OPEN and r["Action"] == "review")
    blocked = todo.blocked()
    print(f"{remaining} still ours to do ({reviews} findings to review, {len(blocked)} blocked by others in the list)."
          if remaining else "Nothing open: the list is finished.")
    for r in (x for x in todo.rows if x["Status"] == "filled"):
        print(f"  waiting for Save: {line(r)}")


def cmd_intake(todo, args):
    if args.latest:
        path = intake_mod.latest_notes(seti_dir(args))
        if path is None:
            sys.exit(f"no research-notes report in {seti_dir(args) / 'reports'}")
    elif args.notes:
        path = Path(args.notes)
    else:
        sys.exit("give a research-notes CSV, or --latest")
    notes = intake_mod.read_notes(path)
    label = args.label or path.stem.removesuffix("-research-notes")
    added = intake_mod.intake(todo, notes, label)
    todo.save()
    print(f"{path.name}: {len(notes)} findings, {len(added)} new review tasks"
          + (f" ({len(notes) - len(added)} already in the list)" if len(notes) > len(added) else ""))
    for r in added:
        print(" ", line(r))


def cmd_next(todo, args):
    rows = todo.ready(args.action)[:args.n]
    if not rows:
        blocked = todo.blocked()
        print("Nothing ready." + (f" {len(blocked)} open tasks are blocked; see status." if blocked else ""))
        return
    if args.batch:
        for r in rows:
            r["Batch"] = args.batch
        todo.save()
    for r in rows:
        print(line(r))


def cmd_show(todo, args):
    for tid in args.ids:
        r = todo.get(tid)
        print(line(r))
        for col in ("Route", "Depends On", "Basis", "Source", "SETI Rows", "Batch", "Updated", "SETI Updated", "Notes"):
            if r[col]:
                print(wrap(col, r[col]))
        blockers = todo.blockers(r)
        if blockers:
            print(wrap("Waits for", " ".join(blockers)))
        for link in filter(None, r["Links"].split(" | ")):
            print(f"  {'link':<12} {link}")
        print()


def cmd_add(todo, args):
    fields = {
        "Action": args.action,
        "Summary": args.summary,
        "Route": args.route,
        "Target": args.target,
        "Depends On": " ".join(args.depends or []),
        "Basis": args.basis,
        "Notes": args.note,
    }
    if args.from_task:
        # A change worked out from a finding inherits where it came from and
        # which SETI rows it settles, so the new ID can be traced back.
        origin = todo.get(args.from_task)
        fields["Source"] = args.from_task
        fields["SETI Rows"] = origin["SETI Rows"]
        fields["Links"] = origin["Links"]
        fields["Batch"] = origin["Batch"]
    else:
        fields["Source"] = "conversation"
    if args.seti_rows:
        fields["SETI Rows"] = args.seti_rows
    row = todo.add(**{k: v for k, v in fields.items() if v})
    todo.save()
    print(line(row))


def cmd_set(todo, args):
    row = todo.set_status(args.id, args.status, pandit_id=args.pandit_id, note=args.note)
    if args.batch:
        row["Batch"] = args.batch
    todo.save()
    print(line(row))


def cmd_seti_updates(todo, args):
    if args.mark:
        for tid in args.mark:
            todo.get(tid)["SETI Updated"] = today()
        todo.save()
    rows = [r for r in todo.rows
            if r["Status"] in ("saved", "done") and r["SETI Rows"] and r["Pandit ID"] and not r["SETI Updated"]]
    if not rows:
        print("No SETI rows waiting for a new Pandit ID.")
    for r in rows:
        print(f"{r['ID']}: SETI row(s) {r['SETI Rows']} <- {r['Pandit ID']} ({r['Action']}: {r['Summary']})")


def cmd_awaiting_export(todo, args):
    for r in todo.rows:
        if r["Status"] == "saved" and r["Pandit ID"]:
            print(r["Pandit ID"] if args.ids_only else f"{r['Pandit ID']}\t{r['ID']}\t{r['Updated']}\t{r['Summary']}")


def cmd_reconcile(todo, args):
    path = Path(args.extract) if args.extract else pandit_mod.latest_extract(seti_dir(args))
    if path is None:
        sys.exit(f"no Pandit extract in {seti_dir(args) / 'data' / 'pandit'}; give one with --extract")
    done, missing = pandit_mod.reconcile(todo, path)
    todo.save()
    print(f"{path.name}: {len(done)} saved tasks now done.")
    for r in missing:
        print(f"  not in the export, though saved before it: {line(r)}")


# ---------- parsing ----------

def parser():
    p = argparse.ArgumentParser(prog="python -m intern", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--todo", default=str(TODO), help="the to-do CSV (default: todo/todo.csv)")
    p.add_argument("--seti", help="the SETI checkout (default: $SETI_DIR or ../seti)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="counts, and what waits for Save")

    s = sub.add_parser("intake", help="review tasks from a research-notes report")
    s.add_argument("notes", nargs="?", help="a reports/<stamp>-research-notes.csv")
    s.add_argument("--latest", action="store_true", help="the newest one in SETI's reports/")
    s.add_argument("--label", help="how Source names the report (default: its stamp)")

    s = sub.add_parser("next", help="the next ready tasks")
    s.add_argument("-n", type=int, default=5)
    s.add_argument("--action", choices=ACTIONS)
    s.add_argument("--batch", help="label the tasks shown with this batch name")

    s = sub.add_parser("show", help="every field of some tasks")
    s.add_argument("ids", nargs="+")

    s = sub.add_parser("add", help="add a change task")
    s.add_argument("--action", required=True, choices=ACTIONS)
    s.add_argument("--summary", required=True)
    s.add_argument("--route", choices=ROUTES, help="default: mine (escalate for merge and site-fix)")
    s.add_argument("--target", help="the Pandit ID it's about, or (new)")
    s.add_argument("--depends", nargs="+", metavar="TASK", help="tasks that must be saved first")
    s.add_argument("--basis", help="the evidence for the revision log or issue")
    s.add_argument("--from", dest="from_task", metavar="TASK", help="the review task it was worked out from")
    s.add_argument("--seti-rows", help="SETI rows to update once saved (default: those of --from)")
    s.add_argument("--note")

    s = sub.add_parser("set", help="change a task's status")
    s.add_argument("id")
    s.add_argument("status", choices=STATUSES)
    s.add_argument("--pandit-id", help="the record created or changed")
    s.add_argument("--note")
    s.add_argument("--batch")

    s = sub.add_parser("seti-updates", help="new IDs still to write into the SETI master")
    s.add_argument("--mark", nargs="+", metavar="TASK", help="record that these are now in the SETI master")

    s = sub.add_parser("awaiting-export", help="IDs saved since the last re-export")
    s.add_argument("--ids-only", action="store_true")

    s = sub.add_parser("reconcile", help="after a re-export, mark what it shows as done")
    s.add_argument("--extract", help="a *-extracted-entities-cleaned.csv (default: newest in SETI's data/pandit/)")
    return p


COMMANDS = {
    "status": cmd_status, "intake": cmd_intake, "next": cmd_next, "show": cmd_show, "add": cmd_add,
    "set": cmd_set, "seti-updates": cmd_seti_updates, "awaiting-export": cmd_awaiting_export,
    "reconcile": cmd_reconcile,
}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        todo = TodoList(args.todo)
        COMMANDS[args.command](todo, args)
    except TodoError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
