#!/usr/bin/env python3
"""Create and validate Windows-safe LabVIEW icon asset names."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import string
from pathlib import Path
from typing import Iterable

INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*]')
SALT_RE = re.compile(r"^[a-z0-9]{10}$")
RESERVED_WINDOWS_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}"
    for prefix in ("COM", "LPT")
    for number in range(1, 10)
}
PNG_NAME_RE = re.compile(
    r"^(?P<summary>.+) option (?P<option>[1-9][0-9]*) "
    r"(?P<width>[1-9][0-9]*)x(?P<height>[1-9][0-9]*) "
    r"(?P<salt>[a-z0-9]{10})\.png$"
)
ICO_NAME_RE = re.compile(
    r"^(?P<summary>.+) option (?P<option>[1-9][0-9]*) "
    r"(?P<salt>[a-z0-9]{10})\.ico$"
)


def _is_reserved(name: str) -> bool:
    stem = name.split(".", 1)[0].upper()
    return stem in RESERVED_WINDOWS_NAMES


def sanitize_summary_name(value: str, max_length: int = 40) -> str:
    """Return a readable Windows-safe summary name.

    Invalid characters become spaces instead of being silently joined, and a
    reserved device name gets an `` Icon`` suffix.
    """

    if not isinstance(value, str):
        raise TypeError("summary name must be a string")
    cleaned = INVALID_WINDOWS_CHARS.sub(" ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if cleaned in {"", ".", ".."}:
        cleaned = "Icon"
    if max_length < 1:
        raise ValueError("max_length must be positive")
    cleaned = cleaned[:max_length].rstrip(" .") or "Icon"
    if _is_reserved(cleaned):
        suffix = " Icon"
        cleaned = cleaned[: max(1, max_length - len(suffix))].rstrip(" .") + suffix
    return cleaned


def validate_summary_name(value: str, max_length: int = 40) -> list[str]:
    errors: list[str] = []
    if not value or value in {".", ".."}:
        errors.append("summary name is empty or special")
        return errors
    if len(value) > max_length:
        errors.append(f"summary name exceeds {max_length} characters")
    if value != value.strip() or value.endswith((".", " ")):
        errors.append("summary name has leading/trailing whitespace or punctuation")
    if re.search(r"\s{2,}", value):
        errors.append("summary name contains repeated whitespace")
    if INVALID_WINDOWS_CHARS.search(value):
        errors.append("summary name contains a Windows-invalid character")
    if _is_reserved(value):
        errors.append("summary name is a reserved Windows device name")
    return errors


def generate_salt(existing: Iterable[str] = ()) -> str:
    """Generate a unique ten-character lowercase alphanumeric salt."""

    used = set(existing)
    alphabet = string.ascii_lowercase + string.digits
    for _ in range(1000):
        candidate = "".join(secrets.choice(alphabet) for _ in range(10))
        if candidate not in used:
            return candidate
    raise RuntimeError("unable to generate a unique salt")


def validate_salt(salt: str) -> bool:
    return bool(SALT_RE.fullmatch(salt))


def _validate_common(summary_name: str, option_number: int, salt: str) -> None:
    errors = validate_summary_name(summary_name)
    if errors:
        raise ValueError("invalid summary name: " + "; ".join(errors))
    if not isinstance(option_number, int) or isinstance(option_number, bool) or option_number < 1:
        raise ValueError("option number must be a positive integer")
    if not validate_salt(salt):
        raise ValueError("salt must be exactly 10 lowercase letters or digits")


def png_filename(
    summary_name: str,
    option_number: int,
    width: int,
    height: int,
    salt: str,
) -> str:
    _validate_common(summary_name, option_number, salt)
    if width < 1 or height < 1:
        raise ValueError("PNG dimensions must be positive")
    return f"{summary_name} option {option_number} {width}x{height} {salt}.png"


def ico_filename(summary_name: str, option_number: int, salt: str) -> str:
    _validate_common(summary_name, option_number, salt)
    return f"{summary_name} option {option_number} {salt}.ico"


def parse_asset_filename(filename: str | Path) -> dict[str, object] | None:
    name = Path(filename).name
    match = PNG_NAME_RE.fullmatch(name)
    if match:
        fields = match.groupdict()
        return {
            "type": "png",
            "summary_name": fields["summary"],
            "option_number": int(fields["option"]),
            "width": int(fields["width"]),
            "height": int(fields["height"]),
            "salt": fields["salt"],
        }
    match = ICO_NAME_RE.fullmatch(name)
    if match:
        fields = match.groupdict()
        return {
            "type": "ico",
            "summary_name": fields["summary"],
            "option_number": int(fields["option"]),
            "salt": fields["salt"],
        }
    return None


def validate_option_filenames(filenames: Iterable[str | Path]) -> list[str]:
    parsed = [parse_asset_filename(item) for item in filenames]
    errors: list[str] = []
    if any(item is None for item in parsed):
        errors.append("one or more filenames do not match the asset convention")
        return errors
    assets = [item for item in parsed if item is not None]
    summaries = {str(item["summary_name"]) for item in assets}
    options = {int(item["option_number"]) for item in assets}
    salts = {str(item["salt"]) for item in assets}
    if len(summaries) != 1:
        errors.append("filenames do not share one summary name")
    if len(options) != 1:
        errors.append("filenames do not share one option number")
    if len(salts) != 1:
        errors.append("filenames do not reuse one option salt")
    for summary in summaries:
        errors.extend(validate_summary_name(summary))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", help="requested summary name")
    parser.add_argument("--option", type=int, default=1)
    parser.add_argument("--salt", help="existing permanent salt")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    summary = sanitize_summary_name(args.summary)
    salt = args.salt or generate_salt()
    _validate_common(summary, args.option, salt)
    result = {"summary_name": summary, "option_number": args.option, "salt": salt}
    print(json.dumps(result, indent=2) if args.as_json else f"{summary}\n{salt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
