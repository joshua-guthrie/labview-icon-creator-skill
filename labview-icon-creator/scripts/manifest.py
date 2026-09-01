#!/usr/bin/env python3
"""Build manifest.json for accepted LabVIEW icon deliverables."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from . import SKILL_VERSION
except ImportError:  # Direct script execution.
    SKILL_VERSION = "1.0.0"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _accepted_option(option: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    source = str(option["source_file"])
    derivatives = [
        {"file": str(item["file"]), "dimensions": list(item["dimensions"])}
        for item in option["derived_png_files"]
    ]
    ico = str(option["ico_file"])
    filenames = [source, *(item["file"] for item in derivatives), ico]
    hashes: dict[str, str] = {}
    for filename in filenames:
        path = base_dir / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"accepted deliverable missing or empty: {filename}")
        hashes[filename] = sha256_file(path)
    return {
        "option_number": int(option["option_number"]),
        "concept_summary": str(option.get("concept_summary", "")),
        "salt": str(option["salt"]),
        "source_file": source,
        "source_dimensions": list(option["source_dimensions"]),
        "derived_png_files": derivatives,
        "ico_file": ico,
        "qa_status": "PASS",
        "sha256": hashes,
    }


def build_manifest(
    run_id: str,
    request: str,
    summary_name: str,
    options: Iterable[dict[str, Any]],
    base_dir: str | Path = ".",
    skill_version: str = SKILL_VERSION,
) -> dict[str, Any]:
    base = Path(base_dir)
    accepted = [option for option in options if option.get("qa_status") == "PASS"]
    manifest_options = [_accepted_option(option, base) for option in accepted]
    salts = [option["salt"] for option in manifest_options]
    if len(salts) != len(set(salts)):
        raise ValueError("accepted options must use unique salts")
    return {
        "run_id": run_id,
        "request": request,
        "summary_name": summary_name,
        "skill_version": skill_version,
        "options": sorted(manifest_options, key=lambda option: option["option_number"]),
    }


def write_manifest(
    destination: str | Path,
    run_id: str,
    request: str,
    summary_name: str,
    options: Iterable[dict[str, Any]],
    base_dir: str | Path = ".",
    skill_version: str = SKILL_VERSION,
) -> Path:
    document = build_manifest(run_id, request, summary_name, options, base_dir, skill_version)
    path = Path(destination)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--summary-name", required=True)
    parser.add_argument("--option-metadata", type=Path, action="append", required=True)
    parser.add_argument("--base-dir", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("manifest.json"))
    parser.add_argument("--skill-version", default=SKILL_VERSION)
    args = parser.parse_args()
    options = [json.loads(path.read_text(encoding="utf-8")) for path in args.option_metadata]
    destination = args.output if args.output.is_absolute() else args.base_dir / args.output
    print(write_manifest(
        destination,
        args.run_id,
        args.request,
        args.summary_name,
        options,
        args.base_dir,
        args.skill_version,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
