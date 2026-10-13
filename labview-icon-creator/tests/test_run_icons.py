from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from support import create_source
from scripts.run_icons import (QA_FIELDS, cleanup, finalize, generation_jobs, init_run,
                               load_run, previews, retry, review, write_json)
from scripts.workspace import temporary_directory


class RunTests(unittest.TestCase):
    def make_run(self, root: Path) -> Path:
        plan = {"request": "fixture function", "summary_name": "Fixture Icons", "concepts": [
            {"concept_id": f"concept-{n}", "concept_summary": f"Fixture {n}",
             "signature": {"metaphor": str(n), "composition": str(n)}, "prompt": f"Generate fixture {n}"}
            for n in range(1, 6)]}
        write_json(root / "plan.json", plan)
        return init_run(root / "plan.json", root / "output", root / "work")

    def fill_and_review(self, run: Path) -> dict:
        _, state = load_run(run)
        for n, candidate in enumerate(state["candidates"]):
            create_source(Path(candidate["source_file"]), variant=n)
        # These records simulate human/model acceptance to test deterministic
        # gates; synthetic fixtures do not establish semantic visual quality.
        record = {"candidates": [{"candidate_id": c["candidate_id"], "qa": {
            size: {"result": "WARN" if size == "16x16" else "PASS", "evidence": f"Reviewed fixture {c['candidate_id']} at {size}"}
            for size in QA_FIELDS}} for c in state["candidates"]],
            "distinctness": {"result": "PASS", "candidate_ids": [c["candidate_id"] for c in state["candidates"]],
                             "evidence": "Selected fixture set comparison"}}
        review_file = run.parent / "review.json"
        write_json(review_file, record)
        review(run, review_file)
        return state

    def test_full_batch_preserves_previous_set_and_cleans_only_owned_workspace(self):
        with temporary_directory() as folder:
            root = Path(folder)
            run = self.make_run(root)
            self.fill_and_review(run)
            old = root / "output" / "earlier.png"
            old.write_bytes(b"previous user file")
            original_manifest = root / "output" / "manifest.json"
            original_manifest.write_text("previous manifest")
            result = finalize(run)
            self.assertEqual(result["accepted_options"], 5)
            self.assertEqual(len(list((root / "output").glob("Fixture Icons option *"))), 25)
            self.assertEqual(old.read_bytes(), b"previous user file")
            self.assertEqual(original_manifest.read_text(), "previous manifest")
            document = json.loads(Path(result["manifest"]).read_text())
            self.assertTrue(document["options"][0]["visual_qa"]["checks"]["16x16"]["evidence"])
            self.assertIn("geometry", document["options"][0]["derived_png_files"][0])
            self.assertEqual(len(document["options"][0]["ico_geometry"]), 9)
            self.assertTrue(finalize(run)["already_published"])
            cleanup(run)
            self.assertFalse(run.parent.exists())
            self.assertTrue(old.is_file())

    def test_finalization_requires_actual_visual_evidence(self):
        with temporary_directory() as folder:
            root = Path(folder)
            run = self.make_run(root)
            for c in load_run(run)[1]["candidates"]:
                create_source(Path(c["source_file"]))
            with self.assertRaisesRegex(ValueError, "visual acceptances"):
                finalize(run)
            self.assertEqual(list((root / "output").iterdir()), [])
            with self.assertRaisesRegex(ValueError, "visual acceptances"):
                finalize(run, allow_shortfall=True)

    def test_changed_reviewed_source_is_rejected(self):
        with temporary_directory() as folder:
            run = self.make_run(Path(folder))
            state = self.fill_and_review(run)
            create_source(Path(state["candidates"][0]["source_file"]), variant=9)
            with self.assertRaisesRegex(ValueError, "source changed"):
                finalize(run)

    def test_stale_set_comparison_is_rejected(self):
        with temporary_directory() as folder:
            run = self.make_run(Path(folder))
            self.fill_and_review(run)
            path, state = load_run(run)
            state["distinctness"]["candidate_ids"].pop()
            write_json(path, state)
            with self.assertRaisesRegex(ValueError, "distinctness"):
                finalize(run)

    def test_processing_failure_keeps_sources_and_salts_for_retry(self):
        with temporary_directory() as folder:
            root = Path(folder)
            run = self.make_run(root)
            self.fill_and_review(run)
            with patch("scripts.run_icons.process_icon", side_effect=OSError("staging denied")):
                with self.assertRaisesRegex(OSError, "staging denied"):
                    finalize(run)
            state = load_run(run)[1]
            salts = [c["salt"] for c in state["candidates"]]
            self.assertTrue(all(Path(c["source_file"]).is_file() for c in state["candidates"]))
            self.assertEqual(list((root / "output").iterdir()), [])
            self.assertEqual(generation_jobs(run)["jobs"], [])
            result = finalize(run)
            self.assertEqual([c["salt"] for c in load_run(run)[1]["candidates"]], salts)
            self.assertEqual(result["generated_candidates"], 5)
            self.assertEqual(len(list((root / "output").glob("lessonsLearned *.md"))), 1)

    def test_retry_limits_preserve_each_attempt(self):
        with temporary_directory() as folder:
            run = self.make_run(Path(folder))
            first = load_run(run)[1]["candidates"][0]
            create_source(Path(first["source_file"]))
            second = retry(run, first["candidate_id"], "correct cue")
            third = retry(run, second, "simplify cue")
            with self.assertRaisesRegex(ValueError, "three attempts"):
                retry(run, third, "again")
            replacement = first | {"concept_id": "new-metaphor", "prompt": "different layout"}
            retry(run, third, "", replacement)
            self.assertTrue(Path(first["source_file"]).exists())
            self.assertEqual(len({c["source_file"] for c in load_run(run)[1]["candidates"]}), 8)

    def test_budget_shortfall_does_not_bypass_quality(self):
        with temporary_directory() as folder:
            run = self.make_run(Path(folder))
            first = load_run(run)[1]["candidates"][0]
            for n in range(15):
                retry(run, first["candidate_id"], "", first | {"concept_id": f"retired-{n}"})
            state = load_run(run)[1]
            for c in state["candidates"]:
                create_source(Path(c["source_file"]))
            with self.assertRaisesRegex(ValueError, "budget"):
                retry(run, first["candidate_id"], "again")
            result = finalize(run, allow_shortfall=True)
            self.assertEqual(result["shortfall"], 5)
            self.assertEqual(json.loads(Path(result["manifest"]).read_text())["options"], [])

    def test_cleanup_and_source_paths_cannot_escape_run(self):
        with temporary_directory() as folder:
            root = Path(folder)
            run = self.make_run(root)
            with self.assertRaisesRegex(ValueError, "published"):
                cleanup(run)
            state = load_run(run)[1]
            state["candidates"][0]["source_file"] = str(root / "user.png")
            write_json(run, state)
            with self.assertRaisesRegex(ValueError, "owned candidates"):
                generation_jobs(run)

    def test_preview_and_pending_jobs_use_registered_paths(self):
        with temporary_directory() as folder:
            run = self.make_run(Path(folder))
            state = self.fill_and_review(run)
            self.assertEqual(generation_jobs(run)["jobs"], [])
            self.assertTrue(previews(run).is_file())
            retry(run, state["candidates"][0]["candidate_id"], "simplify")
            self.assertEqual(len(generation_jobs(run)["jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
