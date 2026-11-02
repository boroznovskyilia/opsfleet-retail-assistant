# Implementation plan

Scope: completed assignment analysis/harness initialization, followed by the owner's
requested vision interview, detailed specification and application implementation,
in that order. Publishing and external messages remain separate actions.
Current status and evidence belong only in [progress.json](progress.json).

## Task definitions

- T01.1 Analyze the supplied OpsFleet assignment and the local Resourcing Assistant
  brief, contracts, relevant runtime paths and evaluation evidence; import the committed
  template_proj harness into this existing repository. Preserve the original assignment,
  initialize project-specific scope and task state, and explain differences in agent
  control, text-to-SQL, RAG, safety and delivery. Acceptance: source-grounded analysis
  and corner cases are documented; generic harness scripts remain unchanged; make check
  and whitespace checks pass; Russian explanation is delivered. Do not change either
  source repository, copy credentials/runtime data, run paid models, or implement the app.

- T02.1 Evaluate workflow versus tool-loop architecture and conduct a staged vision
  interview. Inputs: original assignment, prior comparison and owner answers. Cover
  success/scope, representative analysis, metric definitions, identity/product grants,
  PII, evidence/causal wording, reports/deletion, Golden knowledge, learning/persona,
  recovery/cost, evaluation and setup. Record accepted choices separately from
  recommendations; resolve material contradictions before dependent work. Acceptance:
  architecture tradeoffs are explained in Russian, the essential vision decisions
  are recorded, and remaining engineering defaults are explicit. Documentation/tooling
  checks only; no source-project modification or premature retail implementation.
- T02.2 Produce the detailed retail specification, concrete production HLD and bounded
  prototype implementation plan after T02.1. Acceptance: requirements, data/metric
  contracts, agent/tool boundaries, authorization/PII, report-confirmation protocol,
  recovery/observability and executable acceptance plan agree with the owner vision.
  Select services/frameworks with reasons; distinguish production design from prototype
  obligations and surface unresolved dependent choices before implementation.
- T02.3 Implement and verify the agreed prototype after T02.2, refining this package
  into dependency-ordered tasks once its architecture/contracts are concrete. Acceptance:
  actual CLI analysis/follow-ups/reports, guarded BigQuery integration, authorized
  confirmed report deletion, bounded recovery, observability and reproducible setup;
  meaningful checks and honest live-model/data evidence. No publication or external
  messages are included. Missing credentials block only dependent integration checks.

- T02.4 Complete a modularity and requirement-conformance pass requested by the owner.
  Depends on the local T02.3 implementation, not its credential-dependent acceptance.
  Separate graph orchestration, tool dispatch, analysis/knowledge/report services,
  response validation/rendering and durable storage without changing accepted product
  scope. Audit the original obligations and accepted decisions, fix gaps with regression
  checks, add an evidence-linked conformance matrix and test actual process behavior.
  Acceptance: readable responsibility boundaries; all applicable local scenarios pass;
  real integrations run when credentials are available, with honest remaining limits.
  Production-only features remain design deliverables under the accepted scope.

- T03.1 Replace local sqlite3 persistence with SQLAlchemy 2 async sessions, preserving
  the existing database, deletion receipts, ownership and cumulative spend. Propagate
  async calls through services, LangGraph, transport, CLI and evaluation. Replace
  avoidable handwritten database queries/fixture setup with ORM/Core expressions;
  retain SQL as the required guarded text-to-SQL input and independent source oracle.
  Acceptance: existing behavior, legacy-state compatibility, transaction rollback and
  cancellation, independent-session concurrency, process restart, session disposal,
  current dependency lock/docs, local checks and focused live integration all pass.
  Review the final change with ponytail-review; no publication or budget reset.

- T04.1 Publish the accepted project to a public GitHub repository following the
  owner's explicit publication request. Prepare and inspect the exact initial commit,
  exclude credentials/local runtime data, verify local checks, create a new repository
  without overwriting another project, push and verify public visibility/content/HEAD.
  Update delivery references and report the URL. No cloud deployment, paid model rerun,
  budget reset or message to the hiring team is included.

## Execution

Implementation order for T02.3: configuration/persistent store and receipts; SQL AST
policy/scoped warehouse; capped OpenRouter transport and LangGraph/tools; CLI and
educational methods; deterministic/integration checks; setup, example transcript,
evaluation entry point and final contract/evidence review. Real provider/data checks
are separate from local synthetic evidence and wait for credentials. No production
fallback to scripted answers is allowed.

Follow the [workflow](../development/workflow.md), including impact review, conditional
HITL, evidence reassessment and completion. An explicit owner task can authorize its
stated work; do not impose a separate approval gate without a real unresolved decision.
Continue independent work when a dependency is blocked. Follow-ups add definitions
here and matching state in progress.json, preserving useful historical evidence.

Implementation follows the vision/specification sequence explicitly requested by the
owner; it needs no repeat routine start approval once those dependencies are resolved.
Do not import another project's completed tasks or select its stack automatically.
