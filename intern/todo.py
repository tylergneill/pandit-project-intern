"""The intern's to-do list: one CSV of tasks, kept out of git.

Each row is one task. There are two kinds:

- a **review** task: one finding from a SETI research-notes report (a slot
  the research agents left unsettled), still to be looked at;
- a **change** task: one concrete thing to do in Pandit, worked out while
  reviewing a finding (create a person, create a work, add a part-of link,
  fix a title, ask an admin to merge two records, ...).

Reviewing a finding usually closes it and adds one or more change tasks,
which point back to it through their Source. The list is how we know where
the work stands and when we've reached the end: when nothing is open, the
batch is finished.

Order matters in Pandit: a work can't name an author who has no record yet,
and a part can't point to a whole that doesn't exist. So change tasks carry
`Depends On`, and `ready()` only offers a task once everything it depends on
has been saved. Among ready tasks, persons come before works, works before
links, and so on (see ACTIONS).

The file lives at todo/todo.csv in this repo (gitignored). Every write goes
through a temporary file, so an interrupted write never leaves half a list.
"""

import csv
import datetime
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "todo" / "todo.csv"

COLUMNS = [
    "ID",            # T0001, T0002, ... assigned in order, never reused
    "Action",        # one of ACTIONS
    "Route",         # "mine" (Tyler can do it as a regular user) or "escalate" (admins/devs)
    "Target",        # the Pandit ID the task is about, "(new)", or blank
    "Summary",       # what to do, in words
    "Depends On",    # task IDs that must be saved first, space separated
    "Basis",         # the evidence: what the revision log or the issue should rest on
    "Source",        # where it came from: "<report> row <n> <field> <slot>", a task ID, or "conversation"
    "SETI Rows",     # SETI master rows (as a spreadsheet numbers them) to update once this is saved
    "Links",         # e-text and Pandit links worth opening, " | " separated
    "Status",        # one of STATUSES
    "Pandit ID",     # the record created or changed, once saved
    "Batch",         # a label for the batch it was done in
    "Updated",       # date of the last status change (YYYY-MM-DD)
    "SETI Updated",  # date Tyler updated the SETI rows with the new ID, if he has
    "Notes",         # anything else
]

# Action -> rank. Lower ranks are done first among ready tasks: the records a
# change will point to have to exist before the change can point to them.
ACTIONS = {
    "create-person": 1,
    "create-work": 2,
    "link-part-of": 3,        # stored on the part: Works step -> "Part of (Work)"
    "link-translation": 3,
    "link-commentary": 3,
    "set-author": 3,
    "rename": 4,
    "add-alias": 4,
    "edit": 4,                # any other field on an existing record
    "merge": 5,               # always escalated: regular users can't merge
    "site-fix": 5,            # always escalated: a bug or missing field in Pandit itself
    "other": 5,
    "review": 6,              # findings come last, so known work gets finished first
}

ROUTES = ("mine", "escalate")
ALWAYS_ESCALATED = {"merge", "site-fix"}

STATUSES = {
    "todo": "not started",
    "filled": "form filled in Pandit, waiting for Tyler to click Save",
    "saved": "saved in Pandit; waiting for the next re-export to show it",
    "filed": "escalated: issue filed or admin asked; waiting on them",
    "done": "finished (a saved change is done once a re-export shows it; a review once it's been decided)",
    "dropped": "decided not to do",
}
OPEN = {"todo", "filled"}        # still ours to do
SATISFIES = {"saved", "done"}    # a dependency in one of these states no longer blocks

_ID = re.compile(r"^T\d{4,}$")


class TodoError(Exception):
    """Something in the list, or asked of it, that doesn't make sense."""


def today():
    return datetime.date.today().isoformat()


class TodoList:
    """The to-do list, read into memory, changed, and saved back whole."""

    def __init__(self, path=TODO):
        self.path = Path(path)
        self.rows = []
        if self.path.exists():
            with open(self.path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                missing = set(COLUMNS) - set(reader.fieldnames or [])
                if missing:
                    raise TodoError(f"{self.path} lacks columns: {', '.join(sorted(missing))}")
                self.rows = [{c: row.get(c) or "" for c in COLUMNS} for row in reader]
        self.check()

    # ---------- reading ----------

    def get(self, task_id):
        for row in self.rows:
            if row["ID"] == task_id:
                return row
        raise TodoError(f"no task {task_id}")

    def deps(self, row):
        return row["Depends On"].split()

    def blockers(self, row):
        """The tasks this one still waits for."""
        return [d for d in self.deps(row) if self.get(d)["Status"] not in SATISFIES]

    def ready(self, action=None):
        """Open tasks with nothing blocking them, in the order to do them.

        'filled' tasks come first: they only need Tyler's Save. Then 'todo'
        tasks by ACTIONS rank (persons, works, links, edits, escalations,
        reviews), then by ID, which is the order they were added.
        """
        out = [r for r in self.rows
               if r["Status"] in OPEN and not self.blockers(r)
               and (action is None or r["Action"] == action)]
        return sorted(out, key=lambda r: (r["Status"] != "filled", ACTIONS[r["Action"]], r["ID"]))

    def blocked(self):
        return [r for r in self.rows if r["Status"] in OPEN and self.blockers(r)]

    def sources(self):
        return {r["Source"] for r in self.rows if r["Source"]}

    # ---------- changing ----------

    def next_id(self):
        numbers = [int(r["ID"][1:]) for r in self.rows]
        return f"T{(max(numbers) + 1 if numbers else 1):04d}"

    def add(self, **fields):
        """Add a task and return it. Unknown fields are an error; the rest default sensibly."""
        unknown = set(fields) - set(COLUMNS)
        if unknown:
            raise TodoError(f"unknown fields: {', '.join(sorted(unknown))}")
        row = {c: "" for c in COLUMNS}
        row.update({k: str(v) for k, v in fields.items() if v is not None})
        row["ID"] = self.next_id()
        row["Status"] = row["Status"] or "todo"
        row["Route"] = row["Route"] or ("escalate" if row["Action"] in ALWAYS_ESCALATED else "mine")
        row["Updated"] = row["Updated"] or today()
        self.rows.append(row)
        try:
            self.check()
        except TodoError:
            self.rows.pop()
            raise
        return row

    def set_status(self, task_id, status, pandit_id=None, note=None):
        row = self.get(task_id)
        if status not in STATUSES:
            raise TodoError(f"unknown status {status!r}; one of: {', '.join(STATUSES)}")
        blockers = self.blockers(row)
        if status in ("filled", "saved") and blockers:
            # Pandit would refuse it, or it would point at a record that isn't there yet.
            raise TodoError(f"{task_id} still waits for {' '.join(blockers)}; save those first")
        if status == "saved" and row["Action"].startswith("create-") and not (pandit_id or row["Pandit ID"]):
            raise TodoError(f"{task_id} creates a record: give its new Pandit ID with --pandit-id")
        row["Status"] = status
        if pandit_id:
            row["Pandit ID"] = str(pandit_id)
        if note:
            row["Notes"] = f"{row['Notes']} | {note}" if row["Notes"] else note
        row["Updated"] = today()
        self.check()
        return row

    # ---------- checking and saving ----------

    def check(self):
        """Raise TodoError on anything that would make the list mislead us."""
        seen = set()
        for row in self.rows:
            tid = row["ID"]
            if not _ID.match(tid):
                raise TodoError(f"bad task ID {tid!r}")
            if tid in seen:
                raise TodoError(f"task ID {tid} appears twice")
            seen.add(tid)
            if row["Action"] not in ACTIONS:
                raise TodoError(f"{tid}: unknown action {row['Action']!r}; one of: {', '.join(ACTIONS)}")
            if row["Route"] not in ROUTES:
                raise TodoError(f"{tid}: route must be one of {ROUTES}, not {row['Route']!r}")
            if row["Action"] in ALWAYS_ESCALATED and row["Route"] != "escalate":
                raise TodoError(f"{tid}: a {row['Action']} can only be escalated")
            if row["Status"] not in STATUSES:
                raise TodoError(f"{tid}: unknown status {row['Status']!r}")
            if row["Pandit ID"] and not row["Pandit ID"].isdigit():
                raise TodoError(f"{tid}: Pandit ID must be a number, not {row['Pandit ID']!r}")
        for row in self.rows:
            for d in self.deps(row):
                if d not in seen:
                    raise TodoError(f"{row['ID']} depends on {d}, which isn't in the list")
        self._check_cycles()

    def _check_cycles(self):
        """A cycle in Depends On would leave its tasks blocked forever."""
        state = {}  # ID -> "visiting" | "done"

        def visit(tid, path):
            if state.get(tid) == "done":
                return
            if state.get(tid) == "visiting":
                raise TodoError("dependency cycle: " + " -> ".join(path + [tid]))
            state[tid] = "visiting"
            for d in self.deps(self.get(tid)):
                visit(d, path + [tid])
            state[tid] = "done"

        for row in self.rows:
            visit(row["ID"], [])

    def save(self):
        self.check()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".csv.tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(self.rows)
        os.replace(tmp, self.path)
