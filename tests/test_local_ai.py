from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_ai import classify_emotion, retrieve_diary_context


class LocalAiSafetyTests(unittest.TestCase):
    def test_crisis_text_never_reaches_router_or_memory(self) -> None:
        self.assertIsNone(classify_emotion("I want to kill myself"))
        self.assertEqual(
            retrieve_diary_context("I want to kill myself", ["I felt stressed yesterday."]),
            (),
        )

    def test_context_is_relevant_and_limited(self) -> None:
        pages = [
            "I practised arrays for ten minutes after lunch.",
            "The weather was pleasant during my walk.",
            "Arrays still feel difficult, but I started one problem.",
        ]
        result = retrieve_diary_context("I am worried about array practice", pages)
        self.assertEqual(len(result), 2)
        self.assertTrue(all("array" in item.lower() for item in result))

    def test_missing_model_is_a_safe_no_result(self) -> None:
        self.assertIsNone(classify_emotion("I feel nervous", Path("missing.json")))


if __name__ == "__main__":
    unittest.main()
