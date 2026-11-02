# Working in this project

Write repository documentation, specifications, durable instructions, code comments
and product text in English. Respond to the user in their language unless they
request otherwise. Keep filenames and commands unchanged.

## Start and resume

Run `make docs`, `make progress` and `git status --short`. Read
[handoff](docs/plans/handoff.md), then reconcile the current task, next action and
checks in [progress.json](docs/plans/progress.json) with actual files before acting.
Inspect headings before reading a long document; read only relevant primary sources:

- [Product core](docs/product/core.md) and [requirements](docs/specs/requirements.md).
- [Architecture](docs/architecture/overview.md) and [scenario map](docs/specs/README.md).
- [Task definitions](docs/plans/implementation.md) and [workflow](docs/development/workflow.md).
- [Verification commands and limits](docs/development/verification.md).

The plan owns task definitions/dependencies/acceptance; progress.json is the single
live task-status/evidence record. Update it after meaningful status/check/blocker
changes and before handoff. Do not duplicate live statuses in other documents.

## Changes, decisions and autonomy

Initiate the [change/conflict procedure](docs/development/workflow.md#changes-and-contradictions)
when a condition changes, a contradiction/gap appears or a check fails. Identify
contracts/code/checks affected and reassess old evidence. Use human-in-the-loop (HITL)
for unresolved requirement meaning or proposed changes to agreed behavior. An explicit
owner instruction resolving the issue needs no repeat approval. Fix unambiguous bugs,
stale documentation and routine technical choices independently within agreed scope.

Record the actual owner request and authorized scope in progress.json; a request to
implement work can itself authorize it. This template grants no project-specific
permission and imposes no separate planning approval gate on an already explicit task.
Continue independently eligible tasks without routine approval requests. Pending owner
decisions or missing external credentials block only dependent work. Publishing,
deployment, repository sharing and external messages need applicable authorization.

## Completion and maintenance

Before documentation changes, read [documentation rules](docs/document_writing.md).
Update affected contracts, scenarios, callers and checks together. Never weaken a
requirement or test expectation to hide implementation failure. Distinguish original
sources, accepted decisions, engineering defaults and measured evidence.

Perform the [completion review](docs/development/workflow.md#completion-review), run
`make check`, `git diff --check` and relevant existing behavior checks. Report actual
results and remaining limits; tooling checks do not establish application quality.
The status scripts are development tools, not application runtime or a background agent.

## Project boundary

The owner first requested assignment analysis, comparison with
resoursing_assistant_test and transfer of the template_proj harness on 2026-11-02.
The follow-up request authorizes an architecture review and thorough vision interview,
then detailed specification and implementation, in that order. Complete the essential
vision decisions before dependent specs/code; once resolved, continue without a repeat
blanket start approval. Record answers, open questions and engineering defaults in
their primary documents and progress.json. The supplied assignment defines a retail
analytics assistant, not a staffing application.
Do not inherit the comparison project's stack, access model, credentials, runtime
files, completed-task history or application implementation authorization.

The harness was exported from committed template_proj contents while preserving this
repository's existing Git identity. Its scripts are development checks, not a runtime
agent, RAG engine or product evaluation harness. Keep the project usable without
neighboring repositories; introduce local AGENTS.md rules only when needed.
