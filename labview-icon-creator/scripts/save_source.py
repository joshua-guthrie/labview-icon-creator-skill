#!/usr/bin/env python3
"""Save one generated PNG from a local artifact or a data URL on stdin.

The stdin route avoids shell command-length limits and per-chunk shell jobs.
This validates transport, not visual quality; it never edits or normalizes art.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image

MAX_PAYLOAD = 64 * 1024 * 1024


def read_stdin_payload() -> str:
    """Read through a writable PTY without echo or console line-length limits."""
    restore = lambda: None
    if sys.stdin.isatty():
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetStdHandle.argtypes = [wintypes.DWORD]
            kernel.GetStdHandle.restype = wintypes.HANDLE
            kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            handle = kernel.GetStdHandle(-10)
            mode = wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                raise OSError("cannot query stdin console mode")
            # Disable ECHO_INPUT and LINE_INPUT while receiving the payload.
            if not kernel.SetConsoleMode(handle, mode.value & ~6):
                raise OSError("cannot disable stdin console echo")
            restore = lambda: kernel.SetConsoleMode(handle, mode.value)
        else:
            import termios
            previous = termios.tcgetattr(sys.stdin.fileno())
            current = list(previous)
            current[3] &= ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, current)
            restore = lambda: termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, previous)
    try:
        print("READY", flush=True)
        return sys.stdin.readline(MAX_PAYLOAD + 2).strip()
    finally:
        restore()


def decode_payload(payload: str) -> bytes:
    if not payload.startswith("data:image/png;base64,"):
        raise ValueError("expected a PNG data URL")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("image payload exceeds the transport limit")
    try:
        return base64.b64decode(payload.split(",", 1)[1], validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid PNG base64 payload") from exc


def save_source(destination: str | Path, *, source: str | Path | None = None,
                payload: str | None = None) -> dict:
    if (source is None) == (payload is None):
        raise ValueError("provide exactly one local source or data URL")
    encoded = Path(source).read_bytes() if source is not None else decode_payload(payload)
    if len(encoded) > MAX_PAYLOAD:
        raise ValueError("image exceeds the transport limit")
    with Image.open(io.BytesIO(encoded)) as image:
        if image.format != "PNG" or image.width != image.height:
            raise ValueError("generated source must be a square PNG")
        dimensions = list(image.size)
        image.verify()
    output = Path(destination).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation keeps concurrent workers and retries from replacing art.
    stream = output.open("xb")
    try:
        with stream:
            stream.write(encoded)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {"source_file": str(output), "dimensions": dimensions,
            "sha256": hashlib.sha256(encoded).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source", type=Path)
    mode.add_argument("--stdin", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = read_stdin_payload() if args.stdin else None
        print(json.dumps(save_source(args.output, source=args.source, payload=payload)))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
