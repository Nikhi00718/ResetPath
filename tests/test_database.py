from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import zipfile

from database import Database
from logic import SupportSettings, Track
from wellbeing import WearableImportRow


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "resetpath-test.db"
        self.database = Database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_schema_reopens(self) -> None:
        reopened = Database(self.database_path)
        self.assertEqual(reopened.list_tasks(), [])

    def test_settings_round_trip(self) -> None:
        settings = SupportSettings(
            trusted_person_name="A Friend",
            trusted_person_phone="+91 99999 99999",
            counsellor_name="Campus Support",
            counsellor_phone="1234567890",
            counsellor_details="Student centre, weekdays",
        )
        self.database.save_settings(settings)
        loaded = self.database.get_settings()
        self.assertEqual(loaded.trusted_person_name, "A Friend")
        self.assertEqual(loaded.counsellor_details, "Student centre, weekdays")

    def test_task_crud_completion_and_reopen(self) -> None:
        task = self.database.add_task(
            "Solve one array problem",
            Track.DSA,
            date.today(),
            15,
        )
        self.assertFalse(task.is_completed)

        self.database.set_task_completed(task.id, True, "I began while anxious.")
        completed = self.database.get_task(task.id)
        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertTrue(completed.is_completed)
        self.assertIn("I began while anxious.", completed.evidence_statement or "")

        self.database.set_task_completed(task.id, False)
        reopened = self.database.get_task(task.id)
        assert reopened is not None
        self.assertFalse(reopened.is_completed)
        self.assertIsNone(reopened.evidence_statement)

        self.assertTrue(
            self.database.update_task(
                task.id,
                "Review two array solutions",
                Track.DSA,
                date.today() + timedelta(days=1),
                20,
            )
        )
        updated = self.database.get_task(task.id)
        assert updated is not None
        self.assertEqual(updated.title, "Review two array solutions")

        self.assertTrue(self.database.delete_task(task.id))
        self.assertIsNone(self.database.get_task(task.id))

    def test_filters_and_progress_rows(self) -> None:
        today_task = self.database.add_task("DBMS notes", Track.CORE_CS, date.today(), 20)
        future_task = self.database.add_task(
            "Project route",
            Track.PROJECT,
            date.today() + timedelta(days=1),
            30,
        )
        self.database.set_task_completed(today_task.id, True)
        today = self.database.list_tasks(date_from=date.today(), date_to=date.today())
        self.assertEqual([task.id for task in today], [today_task.id])
        self.assertEqual(
            [task.id for task in self.database.list_tasks(completed=False)],
            [future_task.id],
        )
        progress = self.database.load_progress_rows()
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["track"], Track.CORE_CS.value)

    def test_thought_entry_round_trip(self) -> None:
        entry = self.database.save_thought_entry(
            "Everyone is ahead",
            "Anxious",
            "A friend has an offer",
            "I completed a project feature",
            "Review one DBMS topic",
            "A grounded response",
        )
        loaded = self.database.list_thought_entries()
        self.assertEqual(loaded[0].id, entry.id)
        self.assertEqual(loaded[0].thought, "Everyone is ahead")

    def test_export_contains_two_csv_files_without_settings(self) -> None:
        self.database.save_settings(
            SupportSettings(
                trusted_person_name="Private Person",
                trusted_person_phone="9999999999",
            )
        )
        self.database.add_task("Apply once", Track.APPLICATIONS, date.today(), 10)
        self.database.save_thought_entry(
            "A thought",
            "Uncertain",
            "Evidence",
            "Other evidence",
            "One action",
            "Response",
        )
        archive_bytes = self.database.create_export_zip()
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {
                    "tasks.csv",
                    "thought_journal.csv",
                    "wearable_context.csv",
                    "mood_checkins.csv",
                },
            )
            combined = (
                archive.read("tasks.csv") + archive.read("thought_journal.csv")
            ).decode("utf-8")
            self.assertNotIn("Private Person", combined)
            self.assertIn("Apply once", combined)
            self.assertIn("A thought", combined)

    def test_wearable_and_mood_context_round_trip(self) -> None:
        imported = self.database.import_wearable_rows(
            (
                WearableImportRow(
                    date.today(),
                    7.25,
                    67,
                    41,
                    6_200,
                    "Test watch",
                ),
            )
        )
        self.assertEqual(imported, 1)
        reading = self.database.list_wearable_readings()[0]
        self.assertEqual(reading.sleep_hours, 7.25)
        self.assertEqual(reading.source, "Test watch")

        checkin = self.database.save_mood_checkin("Okay", 3, "After lunch")
        self.assertEqual(checkin.energy, 3)
        self.assertEqual(self.database.list_mood_checkins()[0].note, "After lunch")

    def test_delete_all_data(self) -> None:
        self.database.save_settings(SupportSettings(trusted_person_name="Friend"))
        self.database.add_task("Task", Track.DSA, date.today())
        self.database.save_thought_entry(
            "Thought", "Anxious", "For", "Against", "Action", "Response"
        )
        self.database.delete_all_data()
        self.assertEqual(self.database.list_tasks(), [])
        self.assertEqual(self.database.list_thought_entries(), [])
        self.assertEqual(self.database.list_wearable_readings(), [])
        self.assertEqual(self.database.list_mood_checkins(), [])
        self.assertEqual(self.database.get_settings(), SupportSettings())


if __name__ == "__main__":
    unittest.main()
