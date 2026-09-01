# LabVIEW Icon Creator skill

The LabVIEW Icon Creator is a production-oriented Codex skill that turns a
short icon request into five distinct, QA-approved LabVIEW VI icon options. For
each accepted option it creates a full-size PNG, three exact-size LabVIEW PNGs,
and a multi-resolution Windows ICO file.

The ready-to-install skill package is in
[`labview-icon-creator/`](labview-icon-creator/). You do not need to build a ZIP
or generate the skill again after cloning this repository.

## What the skill produces

For a normal successful request, the skill creates:

- five independent 1024x1024 source PNG files;
- five 29x29 PNG files;
- five 30x23 PNG files;
- five 30x18 PNG files;
- five multi-resolution Windows ICO files;
- one `manifest.json` containing file metadata and SHA-256 hashes;
- one lessons-learned Markdown file only if generation, processing, or final
  validation encountered a qualifying failure.

Final files are written directly into the working directory where the icon run
is performed. The skill does not create a ZIP unless explicitly asked.

## Requirements

Install these prerequisites on the destination computer before installing the
skill:

1. Git.
2. Codex CLI, the Codex IDE extension, or the ChatGPT desktop app with Codex.
3. Python 3.10 or newer.
4. Pillow 10.x, 11.x, or 12.x in the Python environment used by Codex.
5. Runtime image-generation and image-inspection capabilities. The skill stops
   during preflight if the active Codex environment cannot generate and inspect
   raster images.

See the [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)
for current Codex skill behavior and supported clients.

Check the local prerequisites:

```bash
git --version
python3 --version
```

On native Windows PowerShell, use `git --version` and `py -3 --version`. Windows
Subsystem for Linux (WSL) is the simplest Windows installation path because the
skill's runtime commands use `python3`.

## First-time installation on Linux, macOS, or WSL

### 1. Clone the repository

Choose a permanent parent directory for the repository. The following example
uses the current directory:

```bash
git clone https://github.com/joshua-guthrie/labview-icon-creator-skill.git
cd labview-icon-creator-skill
```

Confirm that the skill entrypoint exists:

```bash
test -f labview-icon-creator/SKILL.md && echo "Skill package found"
```

### 2. Install the Python dependency

Install Pillow into the same Python environment that Codex will use:

```bash
python3 -m pip install --user -r labview-icon-creator/requirements.txt
python3 -c "import PIL; print('Pillow', PIL.__version__)"
```

If your operating system prevents user-level `pip` installations, use an
isolated virtual environment:

```bash
python3 -m venv "$HOME/.venvs/labview-icon-creator"
source "$HOME/.venvs/labview-icon-creator/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r labview-icon-creator/requirements.txt
python -c "import PIL; print('Pillow', PIL.__version__)"
```

When using this virtual environment, activate it before starting Codex from the
terminal so the skill can find Pillow through `python3`.

### 3. Install the skill for your user account

Codex loads personal skills from `$HOME/.agents/skills`. A symbolic link is
recommended because future `git pull` operations update the installed skill
immediately:

```bash
mkdir -p "$HOME/.agents/skills"
ln -s "$(pwd)/labview-icon-creator" "$HOME/.agents/skills/labview-icon-creator"
```

The `ln` command intentionally fails if a skill already exists at that path. If
that happens, inspect the existing folder or link before replacing it:

```bash
ls -ld "$HOME/.agents/skills/labview-icon-creator"
```

If symbolic links are unsuitable, copy the skill instead:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R labview-icon-creator "$HOME/.agents/skills/"
```

A copied installation must be copied again whenever the repository is updated.

### 4. Run the offline test suite

From the repository root, run:

```bash
python3 -m unittest discover -s labview-icon-creator/tests -v
```

The tests use synthetic images and do not call a live image-generation service.
They verify naming, exact PNG dimensions, proportional resizing, ICO frames,
technical validation, manifests, lessons-learned reports, and the complete
25-file output package.

### 5. Start or restart Codex

Codex normally detects skill changes automatically. If the new skill does not
appear, completely restart the Codex client. In Codex CLI or the IDE extension,
run `/skills` and confirm that `labview-icon-creator` is listed.

### 6. Test the installed skill

Explicitly invoke the skill in a new Codex chat:

```text
Use $labview-icon-creator to create five icon options for adding a driver to the system.
```

Codex can also invoke the skill automatically when a request matches the skill's
description.

## First-time installation on native Windows PowerShell

WSL is recommended, but a native PowerShell installation can use a directory
junction. Start PowerShell, choose a permanent parent directory, and run:

```powershell
git clone https://github.com/joshua-guthrie/labview-icon-creator-skill.git
Set-Location labview-icon-creator-skill

py -3 -m pip install --user -r .\labview-icon-creator\requirements.txt
py -3 -c "import PIL; print('Pillow', PIL.__version__)"

$SkillRoot = Join-Path $HOME ".agents\skills"
$SkillSource = (Resolve-Path ".\labview-icon-creator").Path
$SkillDestination = Join-Path $SkillRoot "labview-icon-creator"

New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null
if (Test-Path $SkillDestination) {
    throw "A skill already exists at $SkillDestination; inspect it before replacing it."
}
New-Item -ItemType Junction -Path $SkillDestination -Target $SkillSource
```

Run the tests with:

```powershell
py -3 -m unittest discover -s .\labview-icon-creator\tests -v
```

Restart Codex if necessary, run `/skills`, and invoke the skill with
`$labview-icon-creator`. If the runtime reports that `python3` is unavailable,
use the Linux/macOS instructions inside WSL and start Codex from that WSL
environment.

## Updating an existing installation

Open a terminal in the cloned repository and update only by fast-forwarding the
public `main` branch:

```bash
cd /path/to/labview-icon-creator-skill
git pull --ff-only origin main
python3 -m pip install --user -r labview-icon-creator/requirements.txt
python3 -m unittest discover -s labview-icon-creator/tests -v
```

For PowerShell:

```powershell
Set-Location C:\path\to\labview-icon-creator-skill
git pull --ff-only origin main
py -3 -m pip install --user -r .\labview-icon-creator\requirements.txt
py -3 -m unittest discover -s .\labview-icon-creator\tests -v
```

If the skill was installed with the recommended symbolic link or junction, no
additional installation step is needed after `git pull`. If it was copied,
replace the installed copy with the updated `labview-icon-creator` directory.
Restart Codex if it does not detect the update automatically.

## Repository-scoped installation

The steps above install the skill for the current user on the computer. To make
it available only inside one repository, place or link the skill under that
repository's `.agents/skills` directory instead:

```text
your-project/
└── .agents/
    └── skills/
        └── labview-icon-creator/
            └── SKILL.md
```

Codex scans `.agents/skills` from the current working directory up to the
repository root. Keep only one installed copy with the same skill name in the
active scope to avoid duplicate entries in skill selectors.

## Troubleshooting

### The skill is not listed

- Confirm the exact file path is
  `$HOME/.agents/skills/labview-icon-creator/SKILL.md`.
- Ensure the skill directory was linked or copied, not the repository root.
- Run `/skills` in Codex CLI or the IDE extension.
- Restart Codex after checking the path.

### Pillow is missing

Run:

```bash
python3 -c "import PIL; print(PIL.__version__)"
```

If that fails, install `requirements.txt` into the environment from which Codex
is launched. When using a virtual environment, activate it before starting
Codex.

### Image generation or inspection is unavailable

The complete workflow requires both capabilities. Use a Codex environment that
provides raster image generation and image/vision inspection. The skill will
not substitute placeholder images or claim success without those tools.

### An installation path already exists

Do not overwrite an unknown skill folder. Inspect it first and determine whether
it is an older link/copy of this repository, a locally modified version, or an
unrelated skill. Back up local changes before intentionally replacing it.
