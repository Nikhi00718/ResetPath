from __future__ import annotations

from datetime import date
import unittest

from wellbeing import parse_wearable_file, wearable_template_csv


class WearableImportTests(unittest.TestCase):
    def test_template_parses(self) -> None:
        result = parse_wearable_file("template.csv", wearable_template_csv())
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].recorded_date, date.today())
        self.assertEqual(result.errors, ())

    def test_rejects_out_of_range_values(self) -> None:
        result = parse_wearable_file(
            "bad.csv",
            b"date,sleep_hours,resting_heart_rate,hrv_ms,steps,source\n"
            b"2026-07-25,30,65,40,1000,watch\n",
        )
        self.assertEqual(result.rows, ())
        self.assertIn("sleep_hours", result.errors[0])

    def test_json_readings_parse_without_network(self) -> None:
        payload = (
            b'{"readings":[{"date":"2026-07-25","sleep_hours":7,'
            b'"steps":5000,"source":"watch"}]}'
        )
        result = parse_wearable_file("watch.json", payload)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].steps, 5000)


if __name__ == "__main__":
    unittest.main()
