# Task definitions and durable progress

[implementation.md](implementation.md) owns task meanings, dependencies and acceptance.
[progress.json](progress.json) is the single live record of status, pending questions,
evidence and next action. Resume using [handoff](handoff.md), `make progress` and actual
files. Do not duplicate current status in plans, decisions or handoff.

## Adding work

Use stable task IDs such as `T01.1`. Define each task once as a Markdown list item in
implementation.md, and add a matching progress task in the same order. Start with a
single task for a small change; group complex work into dependency-ordered packages.
Do not create separate ceremonial plans for simple work. Product rules stay in specs.

Each task definition needs enough context to identify inputs, outputs, dependencies,
observable acceptance, meaningful checks and important failure cases. Empty sections
in the template are guidance, not work that has been accepted or completed.

## Progress fields

| Field | Meaning |
| --- | --- |
| authorization.project_work / evidence | Whether project work is authorized, with the actual request and scope; not permission for unrelated external actions |
| current_task | The single in_progress task ID, or null |
| next_action | A concrete resumption step or the pending owner question |
| tasks | Ordered records with id, status, evidence and blocker |
| last_checks | Observed command, result (passed/failed/not_run) and scope |
| blockers / runtime_services | Cross-task blockers and actual service state when applicable; empty in a fresh project |
| updated_at | Last state update with a timezone |

Use not_started/in_progress/blocked/done. Done requires evidence; blocked requires a
concrete reason, including the question/options/impact when HITL is pending. At most
one task may be in_progress. Save full JSON via a temporary file and atomic replace,
then run `make progress`. Store no secrets, raw prompts or environment dumps.

Record actual request-derived scope before starting work; an explicit implementation
request need not be approved again. The shipped seed has no authorization or tasks.
The validator applies the recorded authorization to all task IDs; no first-package
exemption is built into the template. Task dependencies and the meaning of scope are
reviewed by the agent rather than inferred by the validator.

## Changed acceptance and retention

Follow the [change/conflict procedure](../development/workflow.md#changes-and-contradictions).
Reopen invalidated acceptance or add a follow-up for changed scope. Retain original
reports and completed tasks when valid historically; record which evidence needs
rerun or justified reuse. Do not relabel old passes as proof of new behavior.

Retain definitions while progress refers to them. Retire references together before
removing obsolete task definitions; Git preserves history. Lasting reasons belong in
[decisions](../decisions/README.md), current behavior in [specifications](../specs/README.md).
