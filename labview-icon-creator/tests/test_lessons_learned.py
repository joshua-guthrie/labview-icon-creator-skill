from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import SKILL_ROOT  # noqa: F401
from scripts.lessons_learned import write_lessons_learned


class LessonsLearnedTests(unittest.TestCase):
    def test_no_qualifying_failure_creates_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            records = [
                {"qa_stage": "concept_preflight", "result": "FAIL", "rule_id": "CONCEPT-001"},
                {"qa_stage": "visual", "result": "WARN", "rule_id": "VIS-MARGIN-005"},
            ]
            self.assertIsNone(write_lessons_learned(records, directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_failure_creates_one_complete_actionable_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            records = [{
                "run_id": "run-1",
                "skill_version": "1.0.0",
                "option_number": 1,
                "concept_id": "driver-plus",
                "attempt_number": 1,
                "qa_stage": "small_size",
                "rule_id": "SMALL-ACTION-006",
                "result": "FAIL",
                "observed_problem": "The plus disappeared at 30x18.",
                "measured_value": "not recognizable",
                "threshold": "recognizable",
                "likely_cause_hypothesis": "The generated plus used thin strokes.",
                "corrective_instruction": "Use a larger solid plus.",
                "retry_result": "PASS on attempt 2",
            }]
            destination = write_lessons_learned(records, directory, {"python_version": "3.x"}, "k7m2p9x4qa")
            self.assertEqual(destination.name, "lessonsLearned k7m2p9x4qa.md")
            self.assertEqual(len(list(Path(directory).glob("lessonsLearned *.md"))), 1)
            text = destination.read_text()
            for heading in (
                "# LabVIEW Icon Creator — Lessons Learned",
                "## Run Metadata",
                "## Problems Encountered",
                "SMALL-ACTION-006",
                "The plus disappeared at 30x18.",
                "### Script Changes",
                "## Proposed Regression Tests",
                "## Recommended Acceptance Criteria",
                "## Codex Implementation Request",
            ):
                self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()
