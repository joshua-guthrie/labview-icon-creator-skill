#!/usr/bin/env python3
"""Generate one actionable Codex improvement report from qualifying QA failures."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from .naming import generate_salt, validate_salt
except ImportError:  # Direct script execution.
    from naming import generate_salt, validate_salt

EXCLUDED_STAGES = {"concept", "concept_preflight", "planning"}


def qualifying_failures(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for record in records:
        stage = str(record.get("qa_stage", "")).strip().lower()
        if str(record.get("result", "")).upper() != "FAIL" or stage in EXCLUDED_STAGES:
            continue
        rule = str(record.get("rule_id", ""))
        if stage in {"visual", "source_visual", "small", "small_size", "processing", "final_png", "final_ico", "generation_limit"} or rule.startswith(
            ("VIS-", "SMALL-", "FILE-PNG-", "FILE-ICO-", "NAME-", "PROCESS-")
        ):
            failures.append(record)
    return failures


def _value(record: dict[str, Any], key: str, default: str = "Not available") -> str:
    value = record.get(key)
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _recommendations(failures: list[dict[str, Any]]) -> dict[str, list[str]]:
    rules = {str(item.get("rule_id", "")) for item in failures}
    recommendations: dict[str, list[str]] = {
        "skill": [],
        "reference": [],
        "script": [],
        "test": [],
        "prompt": [],
    }
    if any(rule.startswith("SMALL-") for rule in rules):
        recommendations["skill"].append("Require small-preview review before permanent salts or final processing, and reject any vanished essential cue.")
        recommendations["reference"].append("Add the observed disappearing/merging feature to the small-size failure examples with its minimum readable geometry.")
        recommendations["script"].append("Extend preview/metric output to expose the affected feature at 30x18 and 16x16 without changing acceptance thresholds.")
        recommendations["test"].append("Add a synthetic small-size regression fixture reproducing the lost or merged feature and assert that the measurable failure is reported.")
        recommendations["prompt"].append("Render the essential action cue as larger solid geometry with wider separation and remove secondary detail competing for pixels.")
    if any(rule.startswith("VIS-") for rule in rules):
        recommendations["skill"].append("Feed the failed visual rule and observable symptom into the next candidate-specific corrective prompt.")
        recommendations["reference"].append("Add a rule-specific example describing the observed visual defect and the required replacement composition.")
        recommendations["test"].append("Add the failed image pattern to a manual visual regression checklist; do not replace model-based visual review with a pixel-only test.")
        recommendations["prompt"].append("Prevent the observed defect explicitly while retaining one dominant idea, no more than three primary elements, and clear margins.")
    if any(rule.startswith("FILE-ICO-") for rule in rules):
        recommendations["script"].append("Harden ICO creation/validation around the missing or corrupt frame and verify every declared frame by decoding it.")
        recommendations["test"].append("Create an ICO regression test that asserts all required sizes, the ICO signature, and a decodable 256x256 entry.")
    if any(rule.startswith(("FILE-PNG-", "PROCESS-")) for rule in rules):
        recommendations["script"].append("Fail atomically before publishing files when dimensions, proportional geometry, centering, format, or blankness validation fails.")
        recommendations["test"].append("Add a synthetic processing fixture for the exact failed dimensions/geometry and assert no invalid final file is accepted.")
    if any(rule.startswith("NAME-") for rule in rules):
        recommendations["reference"].append("Document the exact filename or salt edge case that failed, including the expected Windows-safe result.")
        recommendations["script"].append("Handle the failed naming case in naming.py before output paths are created.")
        recommendations["test"].append("Add the failed summary, reserved name, salt, or cross-option collision as a naming regression case.")
    for category, fallback in {
        "skill": "Keep the bounded retry and failure-record workflow; add a targeted instruction only for the demonstrated failure mode.",
        "reference": "Document the observed symptom next to its existing stable QA rule without duplicating unrelated guidance.",
        "script": "Preserve current deterministic behavior unless the failure evidence identifies a script defect.",
        "test": "Add a regression at the lowest deterministic layer that can reproduce the failure; use a visual checklist when it cannot be automated.",
        "prompt": "Add a candidate-specific corrective phrase tied to observable evidence; do not broadly relax style or QA constraints.",
    }.items():
        if not recommendations[category]:
            recommendations[category].append(fallback)
    return recommendations


def render_report(
    failures: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> str:
    metadata = metadata or {}
    lines = ["# LabVIEW Icon Creator — Lessons Learned", "", "## Run Metadata", ""]
    metadata_fields = {
        "run_id": metadata.get("run_id") or failures[0].get("run_id"),
        "skill version": metadata.get("skill_version") or failures[0].get("skill_version"),
        "skill Git commit": metadata.get("skill_git_commit"),
        "Python version": metadata.get("python_version"),
        "Pillow version": metadata.get("pillow_version"),
        "image-generation backend/tool": metadata.get("image_generation_backend"),
        "date/time": metadata.get("timestamp") or failures[0].get("timestamp"),
    }
    for key, value in metadata_fields.items():
        if value not in (None, ""):
            lines.append(f"- {key}: {value}")

    counts = Counter(str(item.get("rule_id", "Unspecified")) for item in failures)
    lines.extend([
        "",
        "## Run Summary",
        "",
        f"{len(failures)} qualifying post-generation or processing failure(s) were recorded across {len(counts)} QA rule(s).",
        "",
        "## Problems Encountered",
        "",
    ])
    for index, failure in enumerate(failures, 1):
        measured = _value(failure, "measured_value")
        threshold = _value(failure, "threshold")
        lines.extend([
            f"### Problem {index}",
            f"- Option: {_value(failure, 'option_number')}",
            f"- Concept: {_value(failure, 'concept_id')}",
            f"- Attempt: {_value(failure, 'attempt_number')}",
            f"- Failed QA stage: {_value(failure, 'qa_stage')}",
            f"- Rule ID: {_value(failure, 'rule_id')}",
            f"- Observed behavior: {_value(failure, 'observed_problem')}",
            f"- Measured evidence: value={measured}; threshold={threshold}",
            f"- Likely cause/hypothesis: {_value(failure, 'likely_cause_hypothesis')}",
            f"- Corrective action: {_value(failure, 'corrective_instruction')}",
            f"- Outcome: {_value(failure, 'retry_result')}",
            "",
        ])

    recurring = [f"- `{rule}` occurred {count} time(s)." for rule, count in sorted(counts.items())]
    lines.extend(["## Recurring Patterns", "", *recurring, "", "## Root-Cause Assessment", ""])
    lines.append(
        "The evidence points to the recorded rule-specific generation or deterministic processing defects. "
        "Treat each cause above as a testable technical hypothesis; do not infer unavailable internal model reasoning."
    )

    recs = _recommendations(failures)
    lines.extend(["", "## Recommended Skill Changes", "", "### SKILL.md Changes", "", *[f"- {item}" for item in recs["skill"]]])
    lines.extend(["", "### Reference Documentation Changes", "", *[f"- {item}" for item in recs["reference"]]])
    lines.extend(["", "### Script Changes", "", *[f"- {item}" for item in recs["script"]]])
    lines.extend(["", "### Test Changes", "", *[f"- {item}" for item in recs["test"]]])
    lines.extend(["", "### Prompt/Generation Changes", "", *[f"- {item}" for item in recs["prompt"]]])
    lines.extend([
        "",
        "## Proposed Regression Tests",
        "",
        *[f"- {item}" for item in recs["test"]],
        "",
        "## Recommended Acceptance Criteria",
        "",
        "- The reproduced failure is rejected by the same stable QA rule before publication.",
        "- A corrected candidate passes full-size and all 29x29, 30x23, 30x18, and 16x16 reviews.",
        "- Every deterministic regression test and the complete existing test suite passes.",
        "- No required dimension, ICO frame, naming rule, or unrelated behavior is weakened.",
        "",
        "## Codex Implementation Request",
        "",
        "Analyze the failures and recommendations documented above.",
        "",
        "Modify the LabVIEW Icon Creator skill so these failure modes are less likely to recur.",
        "",
        "Requirements:",
        "",
        "1. Update SKILL.md where appropriate.",
        "2. Update reference documentation where appropriate.",
        "3. Update image-processing or QA scripts where appropriate.",
        "4. Add or modify automated regression tests.",
        "5. Preserve behavior unrelated to these failures.",
        "6. Do not weaken existing QA rules merely to make failures disappear.",
        "7. Prefer preventing bad generation over accepting it.",
        "8. Run the complete existing test suite and the new regression tests.",
        "9. Report exactly which files were changed and why.",
        "",
    ])
    return "\n".join(lines)


def write_lessons_learned(
    records: Iterable[dict[str, Any]],
    output_dir: str | Path = ".",
    metadata: dict[str, Any] | None = None,
    salt: str | None = None,
) -> Path | None:
    failures = qualifying_failures(records)
    if not failures:
        return None
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    existing = {
        path.stem.removeprefix("lessonsLearned ")
        for path in output.glob("lessonsLearned ??????????.md")
    }
    report_salt = salt or generate_salt(existing)
    if not validate_salt(report_salt):
        raise ValueError("lessons-learned salt must be exactly 10 lowercase letters or digits")
    destination = output / f"lessonsLearned {report_salt}.md"
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite lessons-learned report: {destination}")
    destination.write_text(render_report(failures, metadata), encoding="utf-8")
    return destination


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qa_log", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--metadata", type=Path, help="optional run metadata JSON")
    parser.add_argument("--salt", help="fixed report salt, primarily for reproducible tests")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata else None
    destination = write_lessons_learned(read_jsonl(args.qa_log), args.output_dir, metadata, args.salt)
    print(destination if destination else "No qualifying failures; no lessons-learned file created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
