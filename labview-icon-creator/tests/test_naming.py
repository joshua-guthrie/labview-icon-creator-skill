from __future__ import annotations

import re
import unittest

from support import SKILL_ROOT  # noqa: F401 - establishes import path
from scripts.naming import (
    generate_salt,
    ico_filename,
    parse_asset_filename,
    png_filename,
    sanitize_summary_name,
    validate_option_filenames,
    validate_salt,
    validate_summary_name,
)


class NamingTests(unittest.TestCase):
    def test_sanitize_invalid_and_repeated_whitespace(self) -> None:
        self.assertEqual(sanitize_summary_name('  Add:  Driver?  '), "Add Driver")
        self.assertEqual(sanitize_summary_name("name. "), "name")

    def test_reserved_and_special_names_are_safe(self) -> None:
        for raw in ("CON", "prn", "COM1", "LPT9", ".", "..", ""):
            with self.subTest(raw=raw):
                value = sanitize_summary_name(raw)
                self.assertFalse(validate_summary_name(value))
                self.assertNotEqual(value.upper(), raw.upper())

    def test_salt_form_and_uniqueness(self) -> None:
        first = generate_salt()
        second = generate_salt({first})
        self.assertRegex(first, r"^[a-z0-9]{10}$")
        self.assertTrue(validate_salt(second))
        self.assertNotEqual(first, second)

    def test_png_and_ico_names(self) -> None:
        salt = "a1b2c3d4e5"
        png = png_filename("Add Driver", 2, 30, 18, salt)
        ico = ico_filename("Add Driver", 2, salt)
        self.assertEqual(png, "Add Driver option 2 30x18 a1b2c3d4e5.png")
        self.assertEqual(ico, "Add Driver option 2 a1b2c3d4e5.ico")
        self.assertEqual(parse_asset_filename(png)["height"], 18)
        self.assertNotIn("30x18", ico)
        self.assertFalse(validate_option_filenames([png, ico]))

    def test_option_filename_validation_catches_salt_mismatch(self) -> None:
        files = [
            png_filename("Add Driver", 1, 29, 29, "a1b2c3d4e5"),
            ico_filename("Add Driver", 1, "f6g7h8j9k0"),
        ]
        self.assertIn("filenames do not reuse one option salt", validate_option_filenames(files))


if __name__ == "__main__":
    unittest.main()
