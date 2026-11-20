"""Read a Pandit extract, to see which saved changes a re-export now shows.

The extract is Pāṇḍitya's cleaned CSV of a Pandit export, the same one SETI
copies into data/pandit/ with `make pandit-copy`. Its name starts with the
export's date: 2026-10-31-extracted-entities-cleaned.csv. We only need its
IDs and that date.

A saved change counts as done once an export taken after the day it was
saved is here, and, for a newly created record, that export contains its
ID. (An edit to an existing record can't be checked field by field from the
extract; a later export is taken as having it.)
"""

import csv
import datetime
import re
from pathlib import Path

_DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-extracted-entities-cleaned\.csv$")


def latest_extract(seti_dir):
    """The newest extract in SETI's data/pandit/, or None."""
    found = sorted(p for p in Path(seti_dir, "data", "pandit").glob("*.csv") if _DATED.match(p.name))
    return found[-1] if found else None


def export_date(path):
    """The export's date, from the file name."""
    m = _DATED.match(Path(path).name)
    if not m:
        raise ValueError(f"can't read an export date from {Path(path).name}")
    return datetime.date.fromisoformat(m.group(1))


def extract_ids(path):
    """Every work and person ID in the extract."""
    with open(path, encoding="utf-8", newline="") as f:
        return {row["ID"].strip() for row in csv.DictReader(f)}


def reconcile(todo, extract_path):
    """Mark saved tasks done where the extract shows them.

    Returns (done, missing): the tasks marked done, and saved tasks that
    created a record the extract, though newer, doesn't have (worth a look:
    the record may have been deleted or merged, or the save didn't take).
    """
    date = export_date(extract_path)
    ids = extract_ids(extract_path)
    done, missing = [], []
    for row in todo.rows:
        if row["Status"] != "saved" or not row["Updated"]:
            continue
        if datetime.date.fromisoformat(row["Updated"]) >= date:
            continue  # saved on or after the export day: it may not be in it yet
        if row["Action"].startswith("create-") and row["Pandit ID"] not in ids:
            missing.append(row)
            continue
        todo.set_status(row["ID"], "done", note=f"in the export of {date}")
        done.append(row)
    return done, missing
