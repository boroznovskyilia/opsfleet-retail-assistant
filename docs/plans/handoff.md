# Resume after an interruption or a new session

## Recovery order

1. Read [AGENTS.md](../../AGENTS.md). Run `make docs`, `make progress` and
   `git status --short` from the actual repository root.
2. Inspect [progress.json](progress.json): authorization scope, current_task,
   next_action, task blockers/evidence and last_checks. Compare saved state with files,
   the diff and observed processes; an interruption may have left unsaved status.
3. Read the relevant [task definition](implementation.md),
   [contracts](../specs/README.md) and code/checks. Use [README](../../README.md) and
   [verification](../development/verification.md) for actual commands and their limits.
4. If conditions changed, a contract is unclear or records disagree, initiate the
   [change/conflict procedure](../development/workflow.md#changes-and-contradictions).
   Preserve uncommitted work and existing data. Do not reset state, repeat external
   effects or rerun paid calls merely because earlier chat context is absent.
5. Resume independently eligible work. Pending owner decisions block only dependent
   changes. An explicit instruction resolving the issue needs no repeated approval.
   If no work is eligible, save/report the pending question and concrete next step.

## State ownership

Use the [document ownership map](../document_writing.md#document-ownership).
The plan defines work; progress.json owns live status, pending questions, current
service references and evidence links. The [workflow](../development/workflow.md#evidence-and-continuity)
requires saves after meaningful boundaries and before handoff. Do not duplicate current
status, result tables or service IDs here. Verify actual process identity before a
restart and preserve existing runtime data; inspect saved failure artifacts before
repeating expensive operations.

The project includes the retail prototype, detailed contracts, local checks and the
imported harness. Real provider/data checks need user-local credentials. Preserve
.runtime/app.sqlite and the cumulative USD 5 ledger; do not reset it on resume. Recover the actual
request-derived task scope from progress.json. Read the source catalogue before
reusing Resourcing findings: its local single-user access model, Azure stack and
fixture rules are not retail requirements. Neighboring repositories are inspection
sources only and must not be edited as part of this task.

These files support resumption when an agent is started. They do not launch sessions
or background jobs. Tooling tests exercise saved-state loading and corruption rejection,
not actual context compaction or reliable future agent behavior.
