# Verification and evidence limits

## Commands

```sh
make setup
make verify
make evaluate
make doctor
```

`make verify` runs repository tooling and the local application suite without paid
calls. `make evaluate` writes a source-fingerprinted mechanics report. Doctor checks
real credential/schema/provider metadata without model generation; exit 1 indicates
readiness failure. [Setup](setup.md) explains local credentials and no-billing checks.

## Recorded local evidence — 2026-11-02

- **67 application tests** cover real SQL parsing/compilation, synthetic four-table
  execution, real SQLAlchemy/SQLite transactions, async LangGraph and actual CLI subprocess
  restart. HTTP/BigQuery SDK network boundaries are explicit test doubles.
- **13 repository tooling tests**, Markdown target and progress validation.
- Ruff formatting/F/E9 checks and wheel/source distribution builds pass. The wheel
  includes every service and the four educational trios.
- A clean export without .env/runtime installs from the lock with
  `uv sync --locked --python 3.12`, then passes all 67 application and 13 tooling
  checks. This setup used cached packages plus dependency downloads; other machines
  need network for missing packages. No other operating system was tested.
- [Local results](../evaluation/local-results.json) preserve the final exact source/
  test/config/lock fingerprint; [live review](../evaluation/live-review.md) separately
  records earlier provider/source/CLI evidence and its version boundaries.
  The [SQLAlchemy review](../evaluation/sqlalchemy-review.md) records current rewrite
  acceptance, 266 fresh numeric comparisons and real async CLI/model/source checks.

| Behavior | Evidence | Limit |
| --- | --- | --- |
| SQL restrictions/PII/scoping/support/metric cohort | [Policy tests](../../tests/test_policy.py) | Synthetic four-table oracle plus separately recorded real checks; no arbitrary-SQL proof |
| Frozen deletion/owner/retry/race/hash/budget | [Store tests](../../tests/test_store.py) | Async SQLAlchemy/SQLite; legacy compatibility, cancellation/rollback, separate sessions, independent engines/processes and disposal; no distributed deployment |
| Iterative agent/clarification/repair/empty/final composition | [Agent tests](../../tests/test_agent.py) | Real graph with scripted test-only model/warehouse; final-call/report behavior also checked live |
| Service boundaries, negated deletion, Golden and retained scan budget | [Service tests](../../tests/test_services.py) | Focused use cases; does not prove all English intent interpretations |
| Key cap/compatible parameters/retry/cost/deadline | [HTTP tests](../../tests/test_llm.py) | MockTransport plus actual Gemini/OpenRouter completion in live cases |
| SDK hard limits/parameters/dry-run/deadline | [Warehouse tests](../../tests/test_warehouse.py) | Real SDK config objects, mocked network, separately verified actual source jobs |
| CLI restart/history/confirmation/missing provider/date redaction | [Process tests](../../tests/test_process.py) | Local subprocess tests plus actual model/data CLI workflow retained in live review |
| No implicit live-evaluation period | [Evaluation test](../../tests/test_evaluation.py) | Runner guard, not semantic report grading |

Fixtures include five CA versus four NY buyers, mixed product grants, cancelled/
returned/out-of-period items and private-name/email canaries. Cases check threshold
before LIMIT, pseudonymous ranking exception, one shared repair, no refund of uncertain
spend/scan reservations and safe tool-free final composition.

## SQLAlchemy rewrite verification

The latest owner-requested migration uses SQLAlchemy 2.0.55, aiosqlite 0.22.1 and
sqlalchemy-bigquery 1.17.3 from the lock. The [review/results](../evaluation/sqlalchemy-review.md)
record fresh model/BigQuery/CLI checks and all 67 local tests. Existing user-local rows,
including the salt and prior cumulative spend, were unchanged on opening the database.
Sessions are not shared across tasks or external calls. A synthetic SQLite fixture
created by the pre-migration store exercises the original on-disk format; the runtime
preservation check uses logical row hashes without exposing their contents.

## Earlier real provider/data evidence

Local Google ADC and a dedicated non-resetting USD 5 OpenRouter key are configured;
the development Google project has no linked billing account. Metadata and bounded
reads work. Real cases cover state/frequency/AOV analysis, one-month trend limitations,
requested report/empty product diagnosis and two publishable products. Real CLI covers
analyst_b, ranking, inherited-period follow-up, explicit saving and confirmed deletion
after restart. Independent SQL checked **239 numerical values** and source item grain.

Read [the full review](../evaluation/live-review.md) and [conformance matrix](../evaluation/conformance.md).
The paid analytical run and final store-only revision have distinct preserved
fingerprints. Analytical code was byte-compared unchanged; final store behavior and
all local checks were rerun. Earlier provider/report/UI failures remain retained.

To collect a new explicitly dated review run:

```sh
.venv/bin/python -m retail_assistant.evaluation --live --start 2026-04-01 --end 2026-04-30
```

The runner shares the cumulative ledger and returns review_required/exit 2. It
preserves actual outputs instead of assigning a fake accuracy score. Source-derived
numeric checks and AI-assisted interpretation review do not establish independent
human approval, unseen-question quality, repeated reliability, production load or a
latency SLO. Old Resourcing results only concern that other project.

## Harness, state and confidentiality

Python 3/Make suffice for `make docs`, `make progress` and `make check`; app tests need
locked dependencies. The four imported harness scripts and generic workflow remain
from template commit e4b237b; app commands/runtime exclusions extend Makefile/.gitignore.
Progress checks validate structure/links, not factual truth or application semantics.

Use progress.json for task status. In this uncommitted checkout, run `git diff --check`
and per-file no-index whitespace checks. Exclude the private .env/runtime/cache; keep
the original assignment byte-identical and verify its SHA-256 separately. Never dump
credentials or provider response bodies while diagnosing a failure.

Preserve `.runtime/app.sqlite`: it contains owned history/reports/actions and the
cumulative ledger. Unknown/crash costs remain conservatively reserved. Synthetic tests
isolate temporary databases. Follow [completion review](workflow.md#completion-review).
