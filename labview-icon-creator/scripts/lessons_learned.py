#!/usr/bin/env python3
"""Generate one reusable improvement specification from qualifying QA failures."""

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


DISTINCTNESS_STRATEGY = {
    "title": "Visual concepts converged on the same design",
    "failure_mode": (
        "Concepts with different names or intended explanations can converge on the same "
        "primary metaphor, action cue, and structural composition."
    ),
    "recurrence_conditions": [
        "Concepts are compared by their labels or prose descriptions instead of their visible structure.",
        "Color, rendering style, or minor placement changes are treated as meaningful differentiation.",
        "A generated candidate is reviewed alone rather than against every planned and accepted option.",
    ],
    "prevention_requirements": [
        "Before generation, describe each concept by its primary metaphor, principal objects, action/status cue, composition, and orientation.",
        "Compare those concept signatures pairwise and replace any plan whose primary metaphor and structural composition substantially overlap another option.",
        "Require differentiation in metaphor or composition; palette, stroke, shading, and small positional changes do not establish distinctness.",
    ],
    "detection_requirements": [
        "After generation, compare each candidate with every accepted option for metaphorical and structural similarity under VIS-DISTINCT-012.",
        "Record the overlapping metaphor and composition as observable evidence when rejecting a candidate; do not rely on pixel similarity alone.",
    ],
    "recovery_requirements": [
        "Retire or regenerate the colliding candidate using a different primary metaphor or structural composition.",
        "Do not attempt recovery solely through recoloring, restyling, or minor repositioning.",
    ],
    "skill": [
        "Require a compact visual concept signature and pairwise distinctness check before generation and after each candidate is accepted."
    ],
    "reference": [
        "Define visual concept signatures and distinguish structural differentiation from cosmetic variation in the five-concept guidance."
    ],
    "script": [
        "Keep semantic distinctness as structured visual QA; deterministic code may preserve evidence and report the rule but must not claim that pixel distance proves distinctness."
    ],
    "test": [
        "Add a workflow regression scenario in which differently named plans share a metaphor/composition and must be rejected before generation.",
        "Add a post-generation visual regression scenario in which a candidate duplicates an accepted option and must fail VIS-DISTINCT-012 until its metaphor or composition changes.",
    ],
    "prompt": [
        "When correcting a distinctness collision, name the overlapping visual structure and request a different metaphor or composition rather than a cosmetic variant."
    ],
}

FAMILY_STRATEGIES = {
    "SMALL-": {
        "title": "Essential meaning did not survive raster reduction",
        "failure_mode": "An essential visual cue became unreadable, merged, or disappeared at a required small output size.",
        "recurrence_conditions": [
            "Meaning depends on thin geometry, narrow gaps, small text, or secondary detail.",
            "Full-size appearance is accepted without reviewing every required native-size preview.",
        ],
        "prevention_requirements": [
            "Design essential cues as large solid geometry with enough separation to survive every required output size.",
            "Remove secondary detail that competes with the pixels needed by the primary object and action cue.",
        ],
        "detection_requirements": [
            "Review native 29x29, 30x23, 30x18, and 16x16 previews and record which essential cue changed meaning."
        ],
        "recovery_requirements": [
            "Enlarge or simplify the failed cue, widen required gaps, and regenerate only the affected concept."
        ],
        "skill": ["Require native-size review before permanent salts or final processing."],
        "reference": ["Document geometric causes of cue loss or merging without tying the rule to one icon subject."],
        "script": ["Keep deterministic preview generation available at every required native size."],
        "test": ["Use synthetic fixtures to verify measurable small-size processing behavior, plus visual regression review for semantic recognition."],
        "prompt": ["Make the essential cue larger and simpler and remove competing detail."],
    },
    "FILE-ICO-": {
        "title": "The multi-resolution ICO contract was not satisfied",
        "failure_mode": "A published ICO was missing, corrupt, mislabeled, or lacked one or more required decodable frames.",
        "recurrence_conditions": ["ICO creation succeeds without decoding and checking every required frame before publication."],
        "prevention_requirements": ["Create ICOs in staging and publish atomically only after every required frame decodes at its declared size."],
        "detection_requirements": ["Check the ICO signature, format, required size set, and decoded dimensions for every frame."],
        "recovery_requirements": ["Discard the staged ICO, correct the deterministic processing defect, and rebuild it from the accepted master."],
        "skill": ["Keep final ICO validation mandatory before publication."],
        "reference": ["Specify the complete decodable ICO frame contract."],
        "script": ["Harden ICO creation and validation around the failed frame invariant."],
        "test": ["Create corrupt or incomplete ICO fixtures and assert that staging refuses publication."],
        "prompt": ["Preserve the accepted visual design; an ICO encoding failure is a processing issue, not a generation prompt issue."],
    },
    "FILE-PNG-": {
        "title": "A PNG deliverable violated its deterministic file contract",
        "failure_mode": "A generated PNG had invalid format, dimensions, background, content, naming, or proportional geometry.",
        "recurrence_conditions": ["A processed file can leave staging without all declared output invariants being validated."],
        "prevention_requirements": ["Create outputs in staging and publish atomically only after validating format, dimensions, background mode, content, naming, and geometry."],
        "detection_requirements": ["Report the exact failed invariant with measured and expected values."],
        "recovery_requirements": ["Discard invalid staged files, fix the lowest deterministic layer responsible, and reprocess the accepted source."],
        "skill": ["Keep deterministic final-file validation mandatory."],
        "reference": ["Specify each PNG invariant independently of any one filename or icon subject."],
        "script": ["Fail atomically before publishing a PNG that violates a declared invariant."],
        "test": ["Add a synthetic fixture for the failed invariant and assert that no invalid final file is published."],
        "prompt": ["Preserve the accepted visual design when the defect belongs to deterministic processing."],
    },
    "PROCESS-": {
        "title": "Deterministic processing changed or invalidated accepted artwork",
        "failure_mode": "The processing pipeline distorted, cropped, misplaced, or otherwise invalidated accepted source artwork.",
        "recurrence_conditions": ["Geometry or output invariants are assumed rather than measured during staged processing."],
        "prevention_requirements": ["Measure proportional scale, centering, bounds, and output invariants before publishing staged files."],
        "detection_requirements": ["Report source and rendered geometry with the violated threshold."],
        "recovery_requirements": ["Fix and regression-test the deterministic transformation, then reprocess the unchanged accepted source."],
        "skill": ["Treat processing validation as mandatory and independent of visual source acceptance."],
        "reference": ["Document the deterministic geometry and atomic-publication contract."],
        "script": ["Reject invalid transformations in staging before any final path is replaced."],
        "test": ["Add a synthetic geometry fixture that reproduces the invariant and verifies atomic failure."],
        "prompt": ["Do not regenerate accepted artwork to conceal a deterministic processing failure."],
    },
    "NAME-": {
        "title": "Output identity or filename invariants were violated",
        "failure_mode": "An output name, salt, option identity, or cross-file naming relationship was invalid or ambiguous.",
        "recurrence_conditions": ["Paths are created before names and cross-option identities are normalized and validated."],
        "prevention_requirements": ["Normalize and validate names, salts, option numbers, and collisions before creating output paths."],
        "detection_requirements": ["Validate each filename and the relationships across every file belonging to an option."],
        "recovery_requirements": ["Correct the naming input before publication without changing accepted artwork."],
        "skill": ["Validate permanent identity and filenames before publishing an accepted option."],
        "reference": ["Document the general naming invariant represented by the failure."],
        "script": ["Reject the invalid naming state before output paths are created."],
        "test": ["Add the failed class of naming input as a deterministic regression case."],
        "prompt": ["Do not alter generated artwork for a naming-only failure."],
    },
    "VIS-": {
        "title": "Generated artwork violated a visual QA invariant",
        "failure_mode": "A candidate's visible structure or rendering did not satisfy a required semantic or visual invariant.",
        "recurrence_conditions": ["Generation constraints or review criteria do not explicitly cover the failed visual invariant."],
        "prevention_requirements": ["State the invariant in subject-independent language during planning and generation."],
        "detection_requirements": ["Inspect the generated source and record the visible evidence under the stable QA rule."],
        "recovery_requirements": ["Correct the visual cause identified by the evidence and regenerate only the affected concept."],
        "skill": ["Feed the stable visual rule and observable symptom into candidate-specific correction."],
        "reference": ["Describe the general visible failure class and its acceptance boundary."],
        "script": ["Preserve structured visual-QA evidence; do not substitute pixel metrics for semantic review."],
        "test": ["Add a subject-independent manual visual regression scenario for the failed invariant."],
        "prompt": ["Correct the identified visual invariant while preserving unrelated accepted constraints."],
    },
}

FALLBACK_STRATEGY = {
    "title": "A required workflow invariant failed",
    "failure_mode": "A post-generation workflow result did not satisfy a required invariant.",
    "recurrence_conditions": ["The failed invariant is not prevented or checked at the earliest reliable workflow stage."],
    "prevention_requirements": ["Define the invariant independently of the run example and enforce it at the earliest reliable stage."],
    "detection_requirements": ["Record observable evidence and expected behavior under a stable rule ID."],
    "recovery_requirements": ["Correct the lowest responsible layer and repeat the affected stage without weakening QA."],
    "skill": ["Add a targeted instruction only for the generalized failure mode."],
    "reference": ["Document the invariant and acceptance boundary without embedding request-specific nouns."],
    "script": ["Change deterministic code only when evidence identifies it as the responsible layer."],
    "test": ["Add regression coverage at the lowest reproducible layer and use structured review when automation is unreliable."],
    "prompt": ["Use observable evidence to correct only the affected candidate or stage."],
}


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


def _strategy_for_rule(rule: str) -> dict[str, Any]:
    if rule == "VIS-DISTINCT-012":
        return DISTINCTNESS_STRATEGY
    for prefix, strategy in FAMILY_STRATEGIES.items():
        if rule.startswith(prefix):
            return strategy
    return FALLBACK_STRATEGY


def generalized_lessons(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group incidents by stable rule while keeping examples out of reusable specs."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        grouped.setdefault(str(failure.get("rule_id") or "Unspecified"), []).append(failure)
    lessons = []
    for rule, incidents in grouped.items():
        strategy = _strategy_for_rule(rule)
        lessons.append({
            "rule_id": rule,
            "occurrences": len(incidents),
            "title": strategy["title"],
            "failure_mode": strategy["failure_mode"],
            "recurrence_conditions": list(strategy["recurrence_conditions"]),
            "prevention_requirements": list(strategy["prevention_requirements"]),
            "detection_requirements": list(strategy["detection_requirements"]),
            "recovery_requirements": list(strategy["recovery_requirements"]),
            "skill": list(strategy["skill"]),
            "reference": list(strategy["reference"]),
            "script": list(strategy["script"]),
            "test": list(strategy["test"]),
            "prompt": list(strategy["prompt"]),
            "incidents": incidents,
        })
    return lessons


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _recommendations(lessons: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        category: _unique(item for lesson in lessons for item in lesson[category])
        for category in ("skill", "reference", "script", "test", "prompt")
    }


def render_report(failures: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> str:
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

    lessons = generalized_lessons(failures)
    counts = Counter(str(item.get("rule_id", "Unspecified")) for item in failures)
    lines.extend([
        "", "## Run Summary", "",
        f"{len(failures)} qualifying failure(s) produced {len(lessons)} generalized lesson(s) across {len(counts)} QA rule(s).",
        "", "## Incident Evidence", "",
    ])
    for index, failure in enumerate(failures, 1):
        lines.extend([
            f"### Incident {index}",
            f"- Option: {_value(failure, 'option_number')}",
            f"- Concept: {_value(failure, 'concept_id')}",
            f"- Attempt: {_value(failure, 'attempt_number')}",
            f"- Failed QA stage: {_value(failure, 'qa_stage')}",
            f"- Rule ID: {_value(failure, 'rule_id')}",
            f"- Observed behavior: {_value(failure, 'observed_problem')}",
            f"- Measured evidence: value={_value(failure, 'measured_value')}; threshold={_value(failure, 'threshold')}",
            f"- Likely cause/hypothesis: {_value(failure, 'likely_cause_hypothesis')}",
            f"- Corrective action: {_value(failure, 'corrective_instruction')}",
            f"- Outcome: {_value(failure, 'retry_result')}",
            "",
        ])

    lines.extend(["## Generalized Lessons", ""])
    for index, lesson in enumerate(lessons, 1):
        example = lesson["incidents"][0]
        lines.extend([
            f"### Lesson {index}: `{lesson['rule_id']}` — {lesson['title']}", "",
            f"**Generalized failure mode:** {lesson['failure_mode']}", "",
            "**Conditions that allow recurrence:**", "",
            *[f"- {item}" for item in lesson["recurrence_conditions"]], "",
            "**Prevention requirements:**", "",
            *[f"- {item}" for item in lesson["prevention_requirements"]], "",
            "**Detection requirements:**", "",
            *[f"- {item}" for item in lesson["detection_requirements"]], "",
            "**Recovery requirements:**", "",
            *[f"- {item}" for item in lesson["recovery_requirements"]], "",
            "**Example from this run (evidence, not the scope of the rule):** "
            f"Option {_value(example, 'option_number')}, concept `{_value(example, 'concept_id')}`, "
            f"failed because {_value(example, 'observed_problem')}", "",
        ])

    recommendations = _recommendations(lessons)
    lines.extend(["## Implementation Specification", ""])
    for heading, category in (
        ("SKILL.md Changes", "skill"),
        ("Reference Documentation Changes", "reference"),
        ("Script Changes", "script"),
        ("Test Changes", "test"),
        ("Prompt/Generation Changes", "prompt"),
    ):
        lines.extend([f"### {heading}", "", *[f"- {item}" for item in recommendations[category]], ""])

    lines.extend(["## Proposed Regression Tests", ""])
    for index, test in enumerate(recommendations["test"], 1):
        lines.extend([
            f"### Regression test {index}", "",
            "- Setup: Construct a subject-independent fixture or review scenario for this failure class.",
            f"- Action: {test}",
            "- Expected result: The stable QA rule rejects the failure before publication, while a corrected result passes without weakening unrelated rules.",
            "",
        ])

    lines.extend([
        "## Recommended Acceptance Criteria", "",
        "- The generalized requirements apply to future icon subjects without requiring nouns or imagery from this run.",
        "- The reproduced failure is rejected by the same stable QA rule before publication.",
        "- A corrected candidate passes full-size and all 29x29, 30x23, 30x18, and 16x16 reviews.",
        "- Every deterministic regression test and the complete existing test suite passes.",
        "- No required dimension, background-mode contract, ICO frame, naming rule, or unrelated behavior is weakened.",
        "", "## Codex Implementation Request", "",
        "Analyze the incident evidence as examples of the generalized failure modes documented above.", "",
        "Modify the LabVIEW Icon Creator skill so similar failures are prevented or detected across future subjects, without overfitting the implementation to this run.", "",
        "Requirements:", "",
        "1. Update SKILL.md and reference documentation where the generalized control belongs.",
        "2. Update deterministic scripts only when the evidence identifies a script responsibility.",
        "3. Add automated regression tests at reproducible deterministic layers and structured visual scenarios where semantic review is required.",
        "4. Preserve behavior unrelated to these failure modes.",
        "5. Do not weaken existing QA rules merely to make failures disappear.",
        "6. Prefer preventing bad generation over accepting it.",
        "7. Run the complete existing test suite and all new regression tests.",
        "8. Report exactly which files changed, why, and which acceptance criteria were verified.",
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
