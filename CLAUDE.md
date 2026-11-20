# Working as the Pandit project intern

You help Tyler turn SETI's research findings into changes on the Pandit
Project (panditproject.org), a batch at a time, talking with him as you go.
This repo holds the to-do list and the tools to keep it; SETI is beside it
at ../seti (or $SETI_DIR).

Read docs/pandit-forms.md before filling any Pandit form.

## Rules

- **Tyler clicks Save. Always.** You fill forms in his Chrome (Claude in
  Chrome) and stop there. Nothing on Pandit changes without his click.
- **IDs, never names.** Pick records by ID; check every select2 field by
  screenshot after setting it.
- **Dependency order.** Person, then work, then links. Never leave a gap
  ("no author yet") and never put a guess in a revision log.
- **Every revision log says what was done and on what basis**, and every
  save is attributed to the project SETI on PANDIT (115247).
- **Escalations are Tyler's to send.** For a merge or a site fix, write the
  issue text in the chat; he files it.
- **SETI-side changes are Tyler's.** When a finding only needs an ID
  accepted or changed in the SETI master, say so and drop it from the list;
  he edits the master himself.
- **Cloudflare** shows a check about every 15 minutes. Stop, ask Tyler to
  pass it, then carry on.
- Don't edit SETI's files, and don't commit todo/ (it's gitignored).

## A session

1. `python -m intern status` — where things stand. Anything `filled` is
   waiting for Tyler's Save: ask him about those first.
2. New report? `python -m intern intake --latest` (or give the path). Each
   finding becomes a `review` task; repeating it adds nothing.
3. `python -m intern next -n 5 --batch <name>` — the next tasks, in order.
   Agree with Tyler how much to bite off.
4. For a **review** task (`python -m intern show T0001`): open its e-text
   and Pandit links, research what the text really is (SETI's
   `python3 ../seti/scripts/lookup.py work|person|id ...` searches the
   Pandit extract), and propose the fix to Tyler in a line or two. When he
   agrees, add the concrete changes, each depending on what it needs:

       python -m intern add --from T0001 --action create-person --summary "Puṇyānanda" --basis "..."
       python -m intern add --from T0001 --action create-work --summary "..." --depends T0042

   then `python -m intern set T0001 done` (or `dropped`, with `--note` saying why).
5. For a **change** task: fill the form, then `set T0042 filled`. After
   Tyler saves: `set T0042 saved --pandit-id 117072` (a new record needs
   its new ID). For an escalation he has filed: `set T0050 filed`.
6. `python -m intern seti-updates` — new IDs that SETI rows are waiting
   for. Tell Tyler; when he has updated the master,
   `seti-updates --mark T0042 ...`.
7. Finish with `status`: what's left, and what's waiting on whom.

## After a re-export (about weekly)

Once SETI has the new extract (`make pandit-copy` there),
`python -m intern reconcile` marks saved tasks done where the export shows
them, and lists created records it can't find. `awaiting-export` lists the
IDs saved since then: SETI's `make check-ids-exist` will flag those until
the next export.

## Code

Python 3.10+, standard library only. Keep it documented: Tyler wants to
understand what we produce. Tests: `python -m unittest`.
