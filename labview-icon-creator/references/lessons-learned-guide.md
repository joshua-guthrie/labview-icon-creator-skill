# Lessons-learned guide

Read this reference only after a generated image, processing step, or final
file has failed, or the 20-candidate limit prevents five accepted options.

Use `scripts/lessons_learned.py` with the run's JSONL failure log. Create exactly
one `lessonsLearned [10-character salt].md` for the run when at least one
qualifying `FAIL` exists. Create none when there were only concept-preflight
rejections, `WARN`, `PASS`, or `N/A` results.

## Purpose

A lessons-learned file is both an incident record and a reusable improvement
specification. Preserve the run-specific facts as evidence, but do not turn a
particular subject, icon metaphor, filename, or retry into a universal rule.
Generalize each incident into the class of failure that allowed it, the
conditions under which similar failures can recur, and controls that apply to
future requests in any subject domain.

For example, a database-cylinder/arrow/disk duplicate is evidence for the
general failure mode "differently named concepts can converge on the same
visual metaphor and composition." The reusable prevention rule should compare
concepts by visual structure; it should not require future prompts or reference
documentation to mention databases or HDF5.

## Required report content

The report must contain two clearly separated layers:

1. **Incident evidence:** option, concept, attempt, QA stage, rule ID,
   observable behavior/evidence, concise cause hypothesis, corrective action,
   and retry outcome. This layer may be specific to the run.
2. **Generalized lesson and implementation specification:**
   - failure mode stated without request-specific nouns;
   - recurrence conditions;
   - prevention requirements;
   - detection requirements;
   - recovery requirements;
   - focused changes for `SKILL.md`, references, scripts, tests, and prompts;
   - regression-test setup, action, and expected result;
   - acceptance criteria that are observable and do not weaken existing QA.

Use a run incident as a labeled example of the generalized lesson, never as the
scope of the lesson itself. Recommendations such as "prevent the observed
defect," "add the failed pattern," or "document this example" are incomplete
unless they also say what class of defect to prevent, where the control belongs,
and how a future implementation or test can determine success.

When a control cannot be automated reliably, specify a structured visual or
semantic review. Do not propose pixel similarity as a substitute for evaluating
metaphor, composition, recognition, or meaning. Never invent missing metadata
such as a Git commit or image-generation backend, and treat cause statements as
testable hypotheses rather than hidden model reasoning.

End with a Codex implementation request requiring focused updates, preserved
unrelated behavior, new regression coverage, and the complete test suite.
