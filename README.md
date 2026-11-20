# pandit-project-intern
an agentic helper tool for doing bulk modifications of Pandit Project database

SETI's research swarm (`make research` in SETI) leaves notes on the slots it
couldn't settle: works and persons Pandit lacks, records it couldn't be
sure of. Some of those Tyler settles on the SETI side himself. The rest need
changes in Pandit: new works and persons, part-of and translation links,
aliases, titles, and some things only Pandit's admins can do. The intern
reads those notes, keeps a to-do list of them, and works through it with
Tyler a batch at a time, filling Pandit's forms in his browser for him to
save.

Kept beside the `seti` repo, part of neither.

## Pieces

- `intern/todo.py`: the to-do list (`todo/todo.csv`, gitignored). Review
  tasks for findings, change tasks for what to do in Pandit, with routes
  (mine / escalate), statuses and dependencies.
- `intern/intake.py`: reads a SETI `reports/*-research-notes.csv` into
  review tasks.
- `intern/pandit.py`: after a Pandit re-export, marks saved changes done.
- `intern/cli.py`: the commands.
- `CLAUDE.md`: how a Claude session works as the intern.
- `docs/pandit-forms.md`: Pandit's forms, fields and traps, from doing it.

## Use

```
python -m intern intake --latest      # findings from SETI's newest research-notes report
python -m intern next -n 5            # what to do next, in dependency order
python -m intern status               # where things stand
python -m intern --help               # everything else
```

Or run `claude` here and ask the intern to pick up the next batch.

Python 3.10+, no dependencies. Tests: `python -m unittest`.
