# SQLAlchemy migration review

What this change does: Local state now uses SQLAlchemy 2 ORM with aiosqlite and
short-lived AsyncSessions. Trusted BigQuery projections/catalogue use Core; the
LangGraph, services, model transport, CLI and live evaluator now await async calls.

The owner explicitly requested this rewrite (DEC-23). It preserves the public CLI,
owned reports/history/actions, frozen selection/hash protocol, customer aliases and
cumulative USD 5 budget. SQL remains the required text-to-SQL input, its policy and
educational examples, the independent source oracle, and SQLite BEGIN/BEGIN IMMEDIATE
transaction control. The native BigQuery SDK still owns bounded job execution; it
runs in a worker thread rather than sharing an ORM session.

## Session and transaction review

Assumed load: one local interactive CLI, with concurrent tasks/independent processes
exercising the cost and deletion invariants. This is not a multi-worker production
performance claim. Each operation owns one new session/transaction. The context manager
commits or rolls back and closes it; the application context disposes the engine.
No live ORM object, session or transaction crosses an HTTP/warehouse/input boundary.
Ownership checks and effects share one transaction. BEGIN IMMEDIATE precedes the
read/check/write sequence so independent engines/processes cannot reserve the same
budget or execute deletion twice. Failures after deletion but before receipt roll
back both. Cancellation returns the connection and retains uncertain HTTP spend.

## Executed evidence

[Machine-readable results](sqlalchemy-results.json) and [local test results](local-results.json)
share source/test/config/lock/fixture fingerprint
`bca2c6746209a8c08ff0979a9ec74f0dbb1152de42945fb45a7a5bcad144d391`.

- 67 application tests, including legacy files, rollback/cancellation, separate
  sessions, independent engines/processes, frozen titles, receipt idempotency,
  cumulative spend, HTTP boundaries, engine disposal and real CLI restart/Ctrl+C.
- 13 repository tooling checks; Ruff formatting/F/E9; wheel/sdist and package-content
  inspection. A fresh .venv in a clean export without credentials/runtime installed
  from the lock and passed all 67 application and 13 tooling checks; this used cached
  packages plus downloads on the same Mac/Python 3.12.12.
- Actual runtime initialization preserved every existing logical row in all six
  tables, including the alias secret, reports/actions and USD 0.88775 ledger.
- Actual BigQuery Core queries matched **266 numeric values** from the independent
  [source SQL](source-oracle.sql): total/state/month revenue, orders, buyers, items,
  average order value, frequency and spend per buyer. All groups and fact grain matched.
  Both product catalogues returned 50 correctly scoped products.
- A real Gemini/OpenRouter report completed in **23.78s**, used one analytical query,
  included evidence/hypotheses/actions, and saved successfully. A real CLI monthly
  follow-up inherited the period, saved another report, previewed exactly those two,
  restarted, confirmed twice with the same receipt, and retained four history rows.
  That CLI workflow took **13.64s**. Only the two test-created reports were deleted.

The first real catalogue request failed because qualified columns lacked an explicit
source alias. A reproducing assertion failed before the alias fix and passed after it;
current local/live acceptance was repeated. The earlier failure artifact remains in
ignored runtime evidence. The change also exposed a Ctrl+C hang in thread-based stdin;
a real subprocess regression now verifies prompt interruption exits cleanly.

The provider reported USD **0.11785725** usage with a non-resetting USD 5 cap at this
check. The local ledger held USD **0.899753**, including prior conservative reservations;
no ledger reset or price overrun occurred. These amounts measure different things.
Prior [live evidence](live-review.md) remains tied to its original fingerprints.

## Ponytail review

Looks good. Ship. Reviewed mappings/schema compatibility, all store callers and
transaction boundaries, model/warehouse resource handling, SQL parameters/privacy,
process recovery, dependency lock and the connected tests. No unresolved blocker was
found for the stated prototype load.

Verdict: Ship.

Not checked: Independent analyst/UX review, unseen-question reliability, production
load or other operating systems. BigQuery worker-thread cancellation remains best
effort within SDK timeouts; this rewrite does not turn the warehouse into an async ORM.
