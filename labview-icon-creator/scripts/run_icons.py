#!/usr/bin/env python3
"""Manage one icon run: init, jobs, previews, review, retry, finalize, cleanup.

Image generation and semantic review remain model responsibilities. This runner
owns bookkeeping and publishes a fully validated package with concise stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import PIL

try:
    from . import SKILL_VERSION
    from .lessons_learned import write_lessons_learned
    from .manifest import sha256_file, write_manifest
    from .naming import generate_salt, sanitize_summary_name
    from .preview_sheet import create_contact_sheet, validate_source_paths
    from .process_icons import process_icon, publish_staged_files, validate_background_mode
    from .validate_icon_assets import has_failures, validate_package
    from .workspace import create_work_directory, temporary_directory
except ImportError:
    from __init__ import SKILL_VERSION
    from lessons_learned import write_lessons_learned
    from manifest import sha256_file, write_manifest
    from naming import generate_salt, sanitize_summary_name
    from preview_sheet import create_contact_sheet, validate_source_paths
    from process_icons import process_icon, publish_staged_files, validate_background_mode
    from validate_icon_assets import has_failures, validate_package
    from workspace import create_work_directory, temporary_directory

QA_FIELDS = ("source", "29x29", "30x23", "30x18", "16x16")
MAX_CANDIDATES = 20


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    # Replace state atomically, so interruption cannot leave a truncated run.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_run(run_file: str | Path) -> tuple[Path, dict]:
    path = Path(run_file).resolve()
    state = read_json(path)
    work = Path(state["work_dir"]).resolve()
    if path != work / "run.json" or read_json(work / ".owner.json").get("run_id") != state["run_id"]:
        raise ValueError("run file is not inside its owned workspace")
    ids = [c["candidate_id"] for c in state["candidates"]]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate IDs must be unique")
    attempts = {}
    for candidate in state["candidates"]:
        number = candidate["option_number"]
        if type(number) is not int or number not in range(1, 6):
            raise ValueError("option number must be between 1 and 5")
        concept = candidate["concept_id"]
        attempts[concept] = attempts.get(concept, 0) + 1
        if attempts[concept] > 3 or candidate["attempt_number"] != attempts[concept]:
            raise ValueError("concept attempts must be sequential and at most three")
        source = Path(candidate["source_file"]).resolve()
        if source.parent != work / "candidates":
            raise ValueError("candidate source must stay inside the owned candidates directory")
    if len(state["candidates"]) > MAX_CANDIDATES:
        raise ValueError("20-candidate generation limit exceeded")
    return path, state


def candidate_record(plan: dict, number: int, index: int, attempt: int, work: Path) -> dict:
    for field in ("concept_id", "concept_summary", "prompt", "signature"):
        if not plan.get(field):
            raise ValueError(f"concept plan requires {field}")
    candidate_id = f"candidate-{index:02d}"
    return {key: plan[key] for key in ("concept_id", "concept_summary", "prompt", "signature")} | {
        "candidate_id": candidate_id, "option_number": number, "attempt_number": attempt,
        "source_file": str(work / "candidates" / f"{candidate_id}.png"), "qa": {},
    }


def init_run(plan_file: str | Path, output_dir: str | Path,
             work_root: str | Path | None = None) -> Path:
    plan = read_json(plan_file)
    concepts = plan["concepts"]
    if len(concepts) != 5 or len({c["concept_id"] for c in concepts}) != 5:
        raise ValueError("plan exactly five separately identified concepts")
    if not plan.get("request") or not plan.get("summary_name"):
        raise ValueError("request and summary_name are required")
    output = Path(output_dir).resolve()
    background = validate_background_mode(plan.get("background_mode", "white"))
    parent = Path(work_root).resolve() if work_root else Path(tempfile.gettempdir()).resolve()
    if parent == output or output in parent.parents:
        raise ValueError("work root must be outside the final output directory")
    # Check writable locations once using owned temporary files, never existing
    # deliverables. Image/vision tools are checked separately by the agent.
    parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=output):
        pass
    work = create_work_directory(parent)
    run_id = uuid.uuid4().hex
    try:
        (work / "candidates").mkdir()
        candidates = [candidate_record(c, n, n, 1, work) for n, c in enumerate(concepts, 1)]
        state = {"schema_version": 1, "run_id": run_id, "request": plan["request"],
                 "summary_name": sanitize_summary_name(plan["summary_name"]), "background_mode": background,
                 "work_dir": str(work), "output_dir": str(output), "skill_version": SKILL_VERSION,
                 "timestamp": datetime.now(timezone.utc).isoformat(),
                 "runtime": {"python": sys.executable, "python_version": platform.python_version(),
                             "pillow_version": PIL.__version__, "shell": "powershell" if os.name == "nt" else "posix"},
                 "candidates": candidates, "failures": [], "distinctness": {}, "published": False}
        write_json(work / ".owner.json", {"run_id": run_id})
        write_json(work / "run.json", state)
    except BaseException:
        shutil.rmtree(work)
        raise
    return work / "run.json"


def generation_jobs(run_file: str | Path) -> dict:
    _, state = load_run(run_file)
    return {"python": state["runtime"]["python"], "shell": state["runtime"]["shell"],
            "saver": str(Path(__file__).with_name("save_source.py").resolve()),
            "background_mode": state["background_mode"], "concurrency": 2,
            "jobs": [{"candidate_id": c["candidate_id"], "destination": c["source_file"], "prompt": c["prompt"]}
                     for c in state["candidates"] if not Path(c["source_file"]).exists()]}


def previews(run_file: str | Path) -> Path:
    _, state = load_run(run_file)
    # Prefer the latest attempt for each option without including retired art.
    latest = {c["option_number"]: c for c in state["candidates"] if Path(c["source_file"]).is_file()}
    candidates = list(latest.values())
    validate_source_paths(c["source_file"] for c in candidates)
    return create_contact_sheet([{"source": c["source_file"], "label": c["candidate_id"] + "\n" + c["concept_summary"]}
                                 for c in candidates], Path(state["work_dir"]) / "preview.png",
                                background_mode=state["background_mode"])


def accepted_qa(qa: dict) -> bool:
    return all(isinstance(qa.get(field), dict) and qa[field].get("result") in ("PASS", "WARN")
               and bool(qa[field].get("evidence")) for field in QA_FIELDS)


def review(run_file: str | Path, review_file: str | Path) -> None:
    path, state = load_run(run_file)
    if state["published"]:
        raise ValueError("published runs cannot be reviewed again")
    record = read_json(review_file)
    by_id = {c["candidate_id"]: c for c in state["candidates"]}
    for assessment in record.get("candidates", []):
        candidate = by_id[assessment["candidate_id"]]
        validate_source_paths([candidate["source_file"]])
        qa = assessment["qa"]
        if set(qa) != set(QA_FIELDS):
            raise ValueError("review source and every required size separately")
        for size, check in qa.items():
            if check.get("result") not in ("PASS", "FAIL", "WARN", "N/A") or not check.get("evidence"):
                raise ValueError("each QA result requires candidate-specific observed evidence")
            if check["result"] == "FAIL":
                if not check.get("rule_id"):
                    raise ValueError("failed visual checks require a stable rule ID")
                state["failures"].append({"candidate_id": candidate["candidate_id"],
                    "option_number": candidate["option_number"], "concept_id": candidate["concept_id"],
                    "attempt_number": candidate["attempt_number"],
                    "qa_stage": "source_visual" if size == "source" else "small_size",
                    "rule_id": check["rule_id"], "result": "FAIL", "observed_problem": check["evidence"],
                    "measured_value": size, "corrective_instruction": check.get("correction"),
                    "likely_cause_hypothesis": check.get("cause")})
        candidate["qa"] = qa
        candidate["reviewed_sha256"] = sha256_file(candidate["source_file"])
    if "distinctness" in record:
        comparison = record["distinctness"]
        ids = comparison.get("candidate_ids", [])
        if len(ids) != len(set(ids)) or not set(ids).issubset(by_id) or not comparison.get("evidence"):
            raise ValueError("distinctness review needs unique known candidate IDs and visible comparison evidence")
        if comparison.get("result") not in ("PASS", "FAIL"):
            raise ValueError("distinctness result must be PASS or FAIL")
        state["distinctness"] = comparison
        if comparison["result"] == "FAIL":
            state["failures"].append({"qa_stage": "source_visual", "rule_id": "VIS-DISTINCT-012",
                                     "result": "FAIL", "observed_problem": comparison["evidence"]})
    write_json(path, state)


def retry(run_file: str | Path, candidate_id: str, prompt: str, replacement_plan: dict | None = None) -> str:
    path, state = load_run(run_file)
    if state["published"] or len(state["candidates"]) >= MAX_CANDIDATES:
        raise ValueError("run is published or the 20-candidate budget is exhausted")
    old = next(c for c in state["candidates"] if c["candidate_id"] == candidate_id)
    plan = replacement_plan or (old | {"prompt": prompt})
    attempts = sum(c["concept_id"] == plan["concept_id"] for c in state["candidates"])
    if attempts >= 3:
        raise ValueError("retire this concept after three attempts; supply a different replacement plan")
    if not prompt and replacement_plan is None:
        raise ValueError("supply a corrective prompt")
    candidate = candidate_record(plan, old["option_number"], len(state["candidates"]) + 1, attempts + 1,
                                 Path(state["work_dir"]))
    state["candidates"].append(candidate)
    state["distinctness"] = {}  # The final comparison must include replacements.
    write_json(path, state)
    return candidate["candidate_id"]


def finalize(run_file: str | Path, allow_shortfall: bool = False) -> dict:
    path, state = load_run(run_file)
    output = Path(state["output_dir"])
    if state["published"]:
        manifest_path = output / state["manifest_file"]
        manifest = read_json(manifest_path)
        checks = validate_package(manifest["options"], output)
        if has_failures(checks) or any(sha256_file(output / name) != expected
            for option in manifest["options"] for name, expected in option["sha256"].items()):
            raise ValueError("previously published assets changed; inspect the existing package")
        return {"qa_status": "PASS", "already_published": True, "manifest": str(manifest_path)}
    latest = {c["option_number"]: c for c in state["candidates"]}
    chosen = [c for c in latest.values() if accepted_qa(c["qa"])]
    generated = sum(Path(c["source_file"]).is_file() for c in state["candidates"])
    if len(chosen) != 5 and not (allow_shortfall and generated == MAX_CANDIDATES):
        raise ValueError("five visual acceptances required; shortfall is allowed only at 20 generated candidates")
    for c in chosen:
        if sha256_file(c["source_file"]) != c.get("reviewed_sha256"):
            raise ValueError(f"source changed since visual review: {c['candidate_id']}")
    comparison = state["distinctness"]
    if chosen and (comparison.get("result") != "PASS" or
                   set(comparison.get("candidate_ids", [])) != {c["candidate_id"] for c in chosen}):
        raise ValueError("review the final accepted set for distinctness before publication")
    if len(chosen) < 5:
        state["failures"].append({"qa_stage": "generation_limit", "rule_id": "PROCESS-LIMIT-001",
            "result": "FAIL", "observed_problem": f"20 generated candidates produced {len(chosen)} accepted options"})
    used = {c["salt"] for c in state["candidates"] if "salt" in c}
    for c in chosen:
        if "salt" not in c:
            c["salt"] = generate_salt(used)
            used.add(c["salt"])
    accepted_by_option = {c["option_number"]: c for c in chosen}
    for failure in state["failures"]:
        if failure.get("qa_stage") in ("source_visual", "small_size"):
            corrected = accepted_by_option.get(failure.get("option_number"))
            if corrected:
                failure["retry_result"] = f"PASS after review of {corrected['candidate_id']}"
            elif failure.get("rule_id") == "VIS-DISTINCT-012" and comparison.get("result") == "PASS":
                failure["retry_result"] = "PASS after comparison of the final selected set"
    write_json(path, state)  # Retain permanent salts when deterministic processing is retried.
    work = Path(state["work_dir"])
    try:
        with temporary_directory(prefix="package-", dir=work) as folder:
            package = Path(folder)
            options = []
            for c in chosen:
                metadata = process_icon(c["source_file"], state["summary_name"], c["option_number"], c["salt"],
                                        package, c["concept_summary"], state["background_mode"], work / "staging")
                metadata.update({"concept_id": c["concept_id"], "candidate_id": c["candidate_id"],
                                 "visual_qa": {"checks": c["qa"], "source_sha256": c["reviewed_sha256"],
                                               "distinctness": comparison}})
                options.append(metadata)
            checks = validate_package(options, package)
            write_json(work / "validation.json", {"qa_status": "FAIL" if has_failures(checks) else "PASS", "checks": checks})
            if has_failures(checks):
                raise ValueError("package validation failed; inspect validation.json")
            for failure in state["failures"]:
                if failure.get("qa_stage") == "processing":
                    failure["retry_result"] = "PASS after deterministic processing of unchanged reviewed sources"
            manifest_name = "manifest.json" if not (output / "manifest.json").exists() else f"manifest {state['run_id']}.json"
            write_manifest(package / manifest_name, state["run_id"], state["request"], state["summary_name"],
                           options, package, state["skill_version"])
            write_lessons_learned(state["failures"], package, state | state["runtime"], compact=True)
            names = [p.name for p in package.iterdir() if p.is_file()]
            if any((output / name).exists() for name in names):
                raise FileExistsError("refusing to overwrite an earlier deliverable")
            publish_staged_files(package, output, names)
        state.update({"published": True, "manifest_file": manifest_name, "published_files": names})
        write_json(path, state)
        return {"qa_status": "PASS", "accepted_options": len(options), "shortfall": 5 - len(options),
                "generated_candidates": generated, "check_count": len(checks), "manifest": str(output / manifest_name),
                "diagnostics": str(work / "validation.json")}
    except (OSError, ValueError, RuntimeError) as exc:
        state["failures"].append({"qa_stage": "processing", "rule_id": "PROCESS-STAGING-002",
                                 "result": "FAIL", "observed_problem": str(exc),
                                 "corrective_instruction": "Repair processing/access and retry unchanged reviewed sources."})
        write_json(path, state)
        raise


def cleanup(run_file: str | Path) -> None:
    path, state = load_run(run_file)
    work = path.parent.resolve()
    output = Path(state["output_dir"]).resolve()
    if not state["published"] or work == output or work in output.parents or output in work.parents:
        raise ValueError("cleanup requires a published run with an isolated owned workspace")
    # Ownership marker plus exact resolved workspace identity prevent broad
    # cleanup or removal of earlier sets, unrelated files, or user output.
    shutil.rmtree(work)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--plan", type=Path, required=True)
    init.add_argument("--output-dir", type=Path, default=Path.cwd())
    init.add_argument("--work-root", type=Path)
    for command in ("jobs", "previews", "review", "retry", "finalize", "status", "cleanup"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--run-file", type=Path, required=True)
        if command == "review":
            command_parser.add_argument("--review-file", type=Path, required=True)
        if command == "retry":
            command_parser.add_argument("--candidate-id", required=True)
            command_parser.add_argument("--prompt", default="")
            command_parser.add_argument("--replacement-plan", type=Path)
        if command == "finalize":
            command_parser.add_argument("--allow-shortfall", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = {"run_file": str(init_run(args.plan, args.output_dir, args.work_root)), "status": "READY"}
        elif args.command == "jobs":
            result = generation_jobs(args.run_file)
        elif args.command == "previews":
            result = {"preview": str(previews(args.run_file))}
        elif args.command == "review":
            review(args.run_file, args.review_file)
            result = {"status": "RECORDED"}
        elif args.command == "retry":
            result = {"candidate_id": retry(args.run_file, args.candidate_id, args.prompt,
                read_json(args.replacement_plan) if args.replacement_plan else None)}
        elif args.command == "finalize":
            result = finalize(args.run_file, args.allow_shortfall)
        elif args.command == "cleanup":
            cleanup(args.run_file)
            result = {"status": "CLEANED"}
        else:
            _, state = load_run(args.run_file)
            result = {"run_id": state["run_id"], "published": state["published"],
                      "candidate_count": len(state["candidates"]),
                      "failure_count": len(state["failures"]), "runtime": state["runtime"]}
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, StopIteration) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
