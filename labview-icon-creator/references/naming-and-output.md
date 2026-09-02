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

- a 1024×1024 source PNG with the selected outer background;
- exact 29×29, 30×23, and 30×18 PNG canvases with the selected outer background;
- one true ICO containing 16, 20, 24, 32, 40, 48, 64, 128, and 256 pixel frames.

The script fits proportionally, centers, uses LANCZOS, never stretches, crops,
or independently redraws derivatives. A different generator size may normalize
to 1024×1024 only when it is square; reject a non-square source rather than
distorting it.

The background mode is `white` by default and `transparent` when requested. The
processor first isolates artwork by removing only border-connected near-white
source pixels when conservative safety checks pass; this preserves enclosed
white foreground. It resamples the isolated RGBA artwork before applying the
final background. White files are saved as opaque RGB with exact-white outer
corners; transparent files are saved as RGBA with zero-alpha outer corners. ICO
frames use the same selected background. Foreground integrity takes priority
over background removal.

Use `--background white` or `--background transparent` on
`scripts/process_icons.py`. Omitting the option selects white. Record
`background_mode` in option metadata and `manifest.json`.

## Validation and final directory

Run `validate_icon_assets.py` to confirm each PNG exists, is nonempty, opens as
PNG, has dimensions matching its filename, has the declared background and
canvas/mode, is not blank, and retains proportional artwork. Confirm each ICO
is nonempty, opens as ICO, contains all required frames including a valid
256×256 frame, uses the declared background, and is not a renamed PNG. Validate
summary names, option numbers, salt form/reuse/uniqueness, and Windows filename
safety.

Write accepted files and `manifest.json` directly in the run's current working
directory. `manifest.json` contains only accepted options and includes run ID,
request, summary name, skill version, concept mapping, file dimensions, QA
status, and SHA-256 hashes. The normal result is 25 icon files. Do not leave
rejected candidates, logs, or transient contact sheets there, and do not create
a ZIP or mandatory nested output folder.
