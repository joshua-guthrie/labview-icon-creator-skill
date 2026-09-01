# Lessons-learned guide

Read this reference only after a generated image, processing step, or final
file has failed, or the 20-candidate limit prevents five accepted options.

Use `scripts/lessons_learned.py` with the run's JSONL failure log. Create exactly
one `lessonsLearned [10-character salt].md` for the run when at least one
qualifying `FAIL` exists. Create none when there were only concept-preflight
rejections, `WARN`, `PASS`, or `N/A` results.

The report must identify every problem's option, concept, attempt, QA stage,
rule ID, observable behavior/evidence, concise cause hypothesis, corrective
action, and retry outcome. Summarize frequency and recurring patterns. Give
specific changes for `SKILL.md`, references, scripts, tests, and generation
prompts; propose regression tests and acceptance criteria. Never invent missing
metadata such as a Git commit or backend.

Recommendations must prevent or catch the demonstrated defect and must not
weaken existing QA. End with a Codex implementation request requiring focused
updates, preserved unrelated behavior, new regression coverage, and the full
test suite.
