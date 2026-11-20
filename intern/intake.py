"""Read SETI research-notes reports into review tasks.

`make research-apply` in SETI writes reports/<stamp>-research-notes.csv: one
row per ID slot the research agents left unsettled. Its columns are SETI's
REPORT_COLUMNS (scripts/common.py): Row, Line, Collection, Text Name,
Author Name, Field, Slot, Current, Suggested ID, Suggested Name, Confidence,
Status, Basis, Text Links, Suggested Link, Current Name, Current Link,
Related Links. Status is usually "not found in Pandit" or "below threshold".

Each such row becomes one review task. Nothing here decides what the fix is:
that's worked out with Tyler while reviewing (some findings need no Pandit
change at all, only a SETI-side decision he makes himself).

Intake is safe to repeat: a finding already in the list (same report, row,
field and slot) is skipped, so re-running on the same report adds nothing.
"""

import csv
from pathlib import Path

NEEDED = ["Row", "Collection", "Text Name", "Field", "Slot", "Status", "Basis"]


def read_notes(path):
    """The rows of a research-notes CSV, as dicts. Raises ValueError if it isn't one."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in NEEDED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} doesn't look like a SETI research-notes report; missing {missing}")
        return list(reader)


def latest_notes(seti_dir):
    """The newest reports/*-research-notes.csv in a SETI checkout, or None.

    Report names start with a YYYY-MM-DD-HHMM stamp, so the last one in
    name order is the newest.
    """
    found = sorted(Path(seti_dir, "reports").glob("*-research-notes.csv"))
    return found[-1] if found else None


def source_of(label, note):
    """The key that identifies a finding: report, SETI row, field and slot."""
    return f"{label} row {note['Row']} {note['Field']} {note['Slot']}"


def summary_of(note):
    """One line saying what the finding is, e.g.
    "Work ID 1 for 'Carcāstava' (Muktabodha), by —: not found in Pandit"."""
    author = note.get("Author Name") or "no author"
    text = f"{note['Field']} {note['Slot']} for '{note['Text Name']}' ({note['Collection']}), by {author}: {note['Status']}"
    if note.get("Suggested ID"):
        text += f"; agent suggested {note['Suggested ID']} {note.get('Suggested Name', '')} at {note.get('Confidence', '?')}"
    return text.strip()


def links_of(note):
    """Every link in the note worth opening, one string, ' | ' separated.

    SETI writes Text Links and Related Links one per line, with a label in
    front ('main  https://...', 'author 85292 Utpala  https://...'); those
    lines are kept whole so the label stays with its link.
    """
    parts = []
    for col in ("Text Links", "Suggested Link", "Current Link", "Related Links"):
        for line in (note.get(col) or "").splitlines():
            line = " ".join(line.split())
            if line:
                parts.append(line)
    return " | ".join(parts)


def intake(todo, notes, label):
    """Add a review task to `todo` for each new finding in `notes`. Returns the tasks added."""
    known = todo.sources()
    added = []
    for note in notes:
        source = source_of(label, note)
        if source in known:
            continue
        added.append(todo.add(
            Action="review",
            Target=(note.get("Suggested ID") or note.get("Current", "")).strip().strip("."),
            Summary=summary_of(note),
            Basis=note.get("Basis", ""),
            Source=source,
            **{"SETI Rows": note["Row"]},
            Links=links_of(note),
        ))
        known.add(source)
    return added
