from __future__ import annotations

import unittest

from logic import (
    Track,
    build_evidence_statement,
    build_grounded_response,
    build_support_plan,
    contains_crisis_language,
    normalize_phone_for_uri,
    normalize_text,
    validate_phone,
    validate_reflection,
    validate_task,
)


class NormalizeTextTests(unittest.TestCase):
    def test_normalizes_case_punctuation_and_apostrophes(self) -> None:
        self.assertEqual(normalize_text("  I DON’T—know!! "), "i don t know")


class CrisisLanguageTests(unittest.TestCase):
    def test_matches_explicit_phrases(self) -> None:
        phrases = (
            "I want to kill myself.",
            "I have thoughts of SUICIDE",
            "I don't want to live",
            "I think I would be better-off dead.",
            "I might self-harm",
            "There is no reason to live.",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_crisis_language(phrase))

    def test_checks_across_multiple_fields(self) -> None:
        self.assertTrue(contains_crisis_language("ordinary text", "I may hurt myself"))

    def test_does_not_match_ordinary_placement_fear(self) -> None:
        ordinary = (
            "Everyone is succeeding and I will never get placed.",
            "I am scared about tomorrow's interview.",
            "My project feels impossible today.",
            "This deadline is killing my motivation.",
        )
        for phrase in ordinary:
            with self.subTest(phrase=phrase):
                self.assertFalse(contains_crisis_language(phrase))


class ResponseTests(unittest.TestCase):
    def test_response_uses_only_supplied_content(self) -> None:
        result = build_grounded_response(
            "Everyone will be placed before me",
            "Anxious",
            "Two friends received offers",
            "Other students are also still applying",
            "Solve one array problem",
        )
        self.assertIn("anxious", result)
        self.assertIn("Two friends received offers", result)
        self.assertIn("Other students are also still applying", result)
        self.assertIn("Solve one array problem", result)
        self.assertNotIn("everything will be okay", result.lower())

    def test_evidence_statement_with_and_without_note(self) -> None:
        self.assertEqual(
            build_evidence_statement("One array problem"),
            "I completed “One array problem” today.",
        )
        self.assertEqual(
            build_evidence_statement("One array problem", "I started while anxious."),
            "I completed “One array problem” today. I started while anxious.",
        )

    def test_support_plan_adapts_without_promising_an_outcome(self) -> None:
        comparison = build_support_plan(
            "Everyone is getting placed and I am behind",
            "Anxious",
        )
        self.assertIn("Other people", comparison.grounded_reframe)
        self.assertEqual(len(comparison.actions), 3)
        self.assertEqual(comparison.source_id, "comparison")
        self.assertNotIn("everything will be okay", comparison.grounded_reframe.lower())

        project = build_support_plan("My project bug feels impossible", "Frustrated")
        self.assertTrue(any("function" in action for action in project.actions))


class ValidationTests(unittest.TestCase):
    def test_task_validation(self) -> None:
        self.assertTrue(validate_task("Read DBMS", Track.CORE_CS, 20).is_valid)
        self.assertFalse(validate_task("", Track.CORE_CS, 20).is_valid)
        self.assertFalse(validate_task("Read DBMS", Track.CORE_CS, 0).is_valid)

    def test_reflection_requires_every_field(self) -> None:
        result = validate_reflection("thought", "anxious", "facts", "", "action")
        self.assertFalse(result.is_valid)
        self.assertIn("balancing evidence", result.message)

    def test_phone_helpers(self) -> None:
        self.assertEqual(normalize_phone_for_uri("+91 98765-43210"), "+919876543210")
        self.assertTrue(validate_phone("+91 98765-43210").is_valid)
        self.assertFalse(validate_phone("123").is_valid)


if __name__ == "__main__":
    unittest.main()
