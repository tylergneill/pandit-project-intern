"""pandit-project-intern: helps turn SETI research findings into Pandit Project changes.

The intern never changes Pandit by itself. It keeps a to-do list of findings
and the concrete changes worked out from them, says what is ready to do next
(in dependency order), and records what Tyler saved in Pandit so the new IDs
can flow back into the SETI master.

Modules:
    todo    the to-do list (one CSV, gitignored) and its rules
    intake  reading SETI research-notes reports into review tasks
    pandit  reading a Pandit extract, to reconcile saved tasks after a re-export
    cli     the command line (python -m intern ...)
"""
