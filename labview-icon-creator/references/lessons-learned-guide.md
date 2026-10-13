# Failure reporting

Normal runs create one compact lessons report from observed qualifying failures;
concept planning rejections and WARN-only reviews create none. The runner handles
this automatically. Read this reference only for reporting issues or a requested
detailed improvement specification.

Record candidate/option/concept/attempt, failed stage and stable rule, actual
size, visible symptom or exception, proposed correction, and retry outcome when
known. Missing information stays unavailable. Do not copy identical evidence
across unrelated candidates or invent root causes. Processing and encoding
failures require deterministic recovery with the accepted source, not new art.

The compact report preserves individual incidents and groups generalized lessons
by rule. It is evidence for later review, not an instruction to modify the skill
or run development tests during icon production. `lessons_learned.py --detailed`
retains the full implementation-specification format for an explicitly requested
improvement task. Such changes require the appropriate deterministic regressions,
structured visual scenarios where automation is unsuitable, and the test suite.
