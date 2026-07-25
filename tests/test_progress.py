from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from database import Database
from logic import Track


class ProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "progress.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_pandas_aggregation_counts_tracks_and_minutes(self) -> None:
        tasks = (
            self.database.add_task("Array", Track.DSA, date.today(), 10),
            self.database.add_task("DBMS", Track.CORE_CS, date.today(), 20),
            self.database.add_task(
                "Feature", Track.PROJECT, date.today() - timedelta(days=1), None
            ),
        )
        for task in tasks:
            self.database.set_task_completed(task.id, True)

        frame = pd.DataFrame(self.database.load_progress_rows())
        self.assertEqual(len(frame), 3)
        counts = frame.groupby("track").size().to_dict()
        self.assertEqual(counts[Track.DSA.value], 1)
        self.assertEqual(counts[Track.CORE_CS.value], 1)
        self.assertEqual(int(frame["estimated_minutes"].fillna(0).sum()), 30)

    def test_incomplete_tasks_are_not_returned(self) -> None:
        self.database.add_task("Still open", Track.APPLICATIONS, date.today(), 10)
        self.assertEqual(self.database.load_progress_rows(), [])


if __name__ == "__main__":
    unittest.main()
