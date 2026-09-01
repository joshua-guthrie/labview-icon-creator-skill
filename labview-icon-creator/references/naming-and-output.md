# Naming, processing, and output

Read this reference after an image passes source and small-size visual QA.

## Names and salts

Derive a concise, human-readable, preferably Title Case `summaryName` of roughly
two to five words and at most 40 characters. Normalize it with `naming.py`:
collapse whitespace; replace `< > : " / \\ | ? *`; remove trailing periods and
spaces; disallow `.` and `..`; and protect `CON`, `PRN`, `AUX`, `NUL`, `COM1`–
`COM9`, and `LPT1`–`LPT9`.

After acceptance, generate a unique permanent salt of exactly ten lowercase
letters/digits for each option and reuse it across that option's files.

```text
[summaryName] option [n] [actual width]x[actual height] [salt].png
[summaryName] option [n] [salt].ico
```

## Required files

For every accepted option, `process_icons.py` creates:

- a 1024×1024 white-background source PNG;
- exact 29×29, 30×23, and 30×18 white-background PNG canvases;
- one true ICO containing 16, 20, 24, 32, 40, 48, 64, 128, and 256 pixel frames.

The script fits proportionally, centers, uses LANCZOS, never stretches, crops,
or independently redraws derivatives. A different generator size may normalize
to 1024×1024 only when it is square; reject a non-square source rather than
distorting it.

For ICO artwork, the processor removes only border-connected near-white pixels
when that operation passes conservative safety checks. This preserves enclosed
white foreground. It retains a white background when safe automatic removal is
not possible; foreground integrity takes priority over transparency.

## Validation and final directory

Run `validate_icon_assets.py` to confirm each PNG exists, is nonempty, opens as
PNG, has dimensions matching its filename, has expected canvas/mode, is not
blank, and retains proportional artwork. Confirm each ICO is nonempty, opens as
ICO, contains all required frames including a valid 256×256 frame, and is not a
renamed PNG. Validate summary names, option numbers, salt form/reuse/uniqueness,
and Windows filename safety.

Write accepted files and `manifest.json` directly in the run's current working
directory. `manifest.json` contains only accepted options and includes run ID,
request, summary name, skill version, concept mapping, file dimensions, QA
status, and SHA-256 hashes. The normal result is 25 icon files. Do not leave
rejected candidates, logs, or transient contact sheets there, and do not create
a ZIP or mandatory nested output folder.
