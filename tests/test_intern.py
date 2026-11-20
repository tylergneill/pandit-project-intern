"""Tests for the to-do list, intake and reconcile. Run: python -m unittest

They use small made-up files in a temporary directory, never todo/todo.csv.
"""

import csv
import tempfile
import unittest
from pathlib import Path

from intern import intake, pandit
from intern.todo import TodoError, TodoList

NOTES_HEADER = ["Row", "Line", "Collection", "Text Name", "Author Name", "Field", "Slot", "Current",
                "Suggested ID", "Suggested Name", "Confidence", "Status", "Basis",
                "Text Links", "Suggested Link", "Current Name", "Current Link", "Related Links"]


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.todo = TodoList(self.dir / "todo.csv")


class TestTodo(Base):
    def test_dependency_order(self):
        """A part-of link isn't offered until both the part's work and its author are saved."""
        person = self.todo.add(Action="create-person", Summary="Utpala")
        work = self.todo.add(Action="create-work", Summary="Ajaḍapramātṛsiddhi", **{"Depends On": person["ID"]})
        link = self.todo.add(Action="link-part-of", Summary="part of 88958", **{"Depends On": work["ID"]})
        self.assertEqual([r["ID"] for r in self.todo.ready()], [person["ID"]])
        self.todo.set_status(person["ID"], "saved", pandit_id="117080")
        self.assertEqual([r["ID"] for r in self.todo.ready()], [work["ID"]])
        with self.assertRaises(TodoError):
            self.todo.set_status(link["ID"], "saved")  # its work isn't saved yet

    def test_rank_and_filled_first(self):
        review = self.todo.add(Action="review", Summary="a finding")
        work = self.todo.add(Action="create-work", Summary="w")
        person = self.todo.add(Action="create-person", Summary="p")
        self.assertEqual([r["ID"] for r in self.todo.ready()], [person["ID"], work["ID"], review["ID"]])
        self.todo.set_status(review["ID"], "filled")
        self.assertEqual(self.todo.ready()[0]["ID"], review["ID"])

    def test_create_needs_new_id(self):
        t = self.todo.add(Action="create-work", Summary="w")
        with self.assertRaises(TodoError):
            self.todo.set_status(t["ID"], "saved")

    def test_merge_is_escalated(self):
        self.assertEqual(self.todo.add(Action="merge", Summary="86415 into 87154")["Route"], "escalate")
        with self.assertRaises(TodoError):
            self.todo.add(Action="merge", Summary="x", Route="mine")

    def test_cycle_rejected(self):
        a = self.todo.add(Action="edit", Summary="a")
        b = self.todo.add(Action="edit", Summary="b", **{"Depends On": a["ID"]})
        a["Depends On"] = b["ID"]
        with self.assertRaises(TodoError):
            self.todo.check()

    def test_round_trip(self):
        self.todo.add(Action="add-alias", Summary="Īśvarasiddhi (Utpala)", Target="117069")
        self.todo.save()
        again = TodoList(self.todo.path)
        self.assertEqual(again.rows, self.todo.rows)


class TestIntake(Base):
    def notes(self):
        path = self.dir / "2026-11-19-2039-research-notes.csv"
        write_csv(path, NOTES_HEADER, [
            {"Row": "40", "Collection": "Muktabodha", "Text Name": "Carcāstava", "Author Name": "",
             "Field": "Work ID", "Slot": "1", "Current": "...", "Status": "not found in Pandit",
             "Basis": "searched", "Text Links": "main       https://example.org/a\nextract    https://example.org/b"},
            {"Row": "41", "Collection": "Muktabodha", "Text Name": "Īśvarasiddhi", "Author Name": "Utpala",
             "Field": "Work ID", "Slot": "1", "Current": "...", "Suggested ID": "88958",
             "Suggested Name": "Siddhitrayī", "Confidence": "0.60", "Status": "below threshold", "Basis": "part"},
        ])
        return path

    def test_intake_is_repeatable(self):
        path = self.notes()
        rows = intake.read_notes(path)
        self.assertEqual(len(intake.intake(self.todo, rows, "r1")), 2)
        self.assertEqual(len(intake.intake(self.todo, rows, "r1")), 0)
        first = self.todo.rows[0]
        self.assertEqual(first["Action"], "review")
        self.assertEqual(first["SETI Rows"], "40")
        self.assertEqual(first["Target"], "")
        self.assertIn("main https://example.org/a | extract https://example.org/b", first["Links"])
        self.assertEqual(self.todo.rows[1]["Target"], "88958")

    def test_not_a_report(self):
        bad = self.dir / "x.csv"
        write_csv(bad, ["a"], [{"a": "1"}])
        with self.assertRaises(ValueError):
            intake.read_notes(bad)


class TestReconcile(Base):
    def test_reconcile(self):
        made = self.todo.add(Action="create-work", Summary="w")
        self.todo.set_status(made["ID"], "saved", pandit_id="117069")
        lost = self.todo.add(Action="create-person", Summary="p")
        self.todo.set_status(lost["ID"], "saved", pandit_id="117999")
        late = self.todo.add(Action="rename", Summary="r", Target="96033")
        self.todo.set_status(late["ID"], "saved")
        for r in (made, lost):
            r["Updated"] = "2026-11-20"
        late["Updated"] = "2026-12-05"  # saved after the export: not judged yet
        extract = self.dir / "2026-12-01-extracted-entities-cleaned.csv"
        write_csv(extract, ["Content type", "ID", "Name"], [{"Content type": "Work", "ID": "117069", "Name": "w"}])
        done, missing = pandit.reconcile(self.todo, extract)
        self.assertEqual([r["ID"] for r in done], [made["ID"]])
        self.assertEqual([r["ID"] for r in missing], [lost["ID"]])
        self.assertEqual(late["Status"], "saved")


if __name__ == "__main__":
    unittest.main()
