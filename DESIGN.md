# Design summary

The prototype uses one bounded LangGraph model/tool loop. The LLM chooses subsequent
read-only research, but code owns product scope, PII exclusion, cohort suppression,
period, resource/spend budgets and report confirmation. This preserves exploration
without an unrestricted effectful agent. [Full contract](docs/specs/prototype.md).

LangGraph was selected by the owner and exposes transitions/state without a hidden
hosted platform. The implementation is a hands-on use developed with AI coding
assistance; prior professional tenure/expertise is not asserted. DSPy/FastAPI/React
are not required here. httpx implements the documented OpenRouter wire contract;
BigQuery's maintained client handles ADC/jobs; SQLGlot provides a dialect-aware AST
instead of a regex SELECT guard. SQLAlchemy 2 ORM with aiosqlite owns local SQLite sessions/transactions and restart
persistence; SQLAlchemy Core and the Google dialect build trusted BigQuery queries.
No new vector service or embedding credential is needed for four example methods.

Gemini 3.8 Flash through OpenRouter is the pinned configuration, based on advertised
tools/JSON support and recorded real tool/JSON checks. Those cases do not establish
unseen-question accuracy. Provider preflight requires
a non-resetting <=USD 5 key and price bounds. The local ledger reserves cost before
each physical attempt; unknown/crash costs retain reservations. [Setup](docs/development/setup.md).

The logical sales relation is built by trusted code from orders/order_items/products/
users, with product grants, completed/non-returned status and explicit item-created UTC
period applied before model aggregation. The model never accesses raw PII or chooses
auth variables. Only a documented flat SELECT subset is supported. Code adds cohort
support HAVING before LIMIT; customer ranking permits only pseudonym+amount. The
threshold is an educational disclosure rule, not differential privacy. Field/status/
currency mapping remains provisional until real source verification.

Completed history, exact period, reports, frozen deletion ID/hash sets and receipts are
in local SQLite. Per-turn graph state is ephemeral; interrupted reads are not silently
replayed. Only explicit /confirm ID executes deletion, atomically with the receipt.
Repeated decisions are idempotent; stale/opposite/foreign decisions fail. Library
removal retains chat history. All ordinary outputs, including partial evidence, persist.

The 60s target, six model calls, eight tools, four analytical reads, 256MiB/job and
1GiB/turn are independent limits. One transient retry and one shared output/SQL repair
are bounded; permission denial is final. Verified tables survive explanation failures.
Logs contain correlated metadata rather than raw prompts/results. English is the
verified language. [Checks/limits](docs/development/verification.md).

Production uses authenticated Cloud Run, Cloud SQL/PostgreSQL owned state/pgvector,
GCS approved Golden originals, Vertex AI, Secret Manager and Cloud observability.
Preferences, reviewed learning/prompt releases and a versioned non-developer persona
editor are designed there. [Production HLD](docs/architecture/production.md).
AI assistance covered source analysis, implementation, fixtures, verification and docs;
synthetic tests are explicitly separated from real model/data evaluation.

## Persistence and sessions

The async Store owns one engine/session factory for its context-managed lifetime.
Every operation creates a fresh AsyncSession through async_sessionmaker.begin();
normal exit commits, exceptions/cancellation roll back, and both paths close the
session. expire_on_commit=False avoids implicit attribute refresh after commit; no
lazy ORM relationships or live ORM objects leave the store. Ownership validation and
writes occur in the same transaction. The CLI/evaluator dispose the engine and close
the HTTP/BigQuery clients on exit. Sessions never span LLM calls, warehouse reads or
interactive input. This follows SQLAlchemy's [async session guidance](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html).

SQLite write operations acquire BEGIN IMMEDIATE through a SQLAlchemy begin event
before any read/check/write. This preserves the database-wide cost/deletion lock
across tasks, independent engines and processes; a Python-only lock would not.
Read transactions use BEGIN. These two driver-level commands are intentional SQL:
SQLAlchemy's SQLite isolation names do not express the required locking mode.
The existing table/column/JSON/hash formats are retained; create_all only creates
missing tables, with no destructive schema rewrite or spend/alias reset.

Trusted source joins/projection and the product catalogue are Core expressions.
The Google BigQuery dialect compiles them and SQLGlot converts named placeholders
for the native SDK. The SDK retains per-job dry-run/scan/deadline/cancellation controls;
its bounded synchronous methods run via asyncio.to_thread. The model still generates
SQL as required by the assignment; SQLGlot validates that input before attaching the
trusted source and privacy guard. SQL examples/metric policies and the independent
source oracle remain SQL. ORM does not replace this security boundary.

## Code responsibilities

| Module | Responsibility |
| --- | --- |
| [agent.py](src/retail_assistant/agent.py) | Conversation lifecycle, LangGraph transitions and shared turn/repair budget |
| [tools.py](src/retail_assistant/tools.py) | Tool contracts, argument parsing and dispatch into services |
| [analysis service](src/retail_assistant/services/analysis.py) | Period/schema gate, read/scan budget and verified evidence |
| [knowledge service](src/retail_assistant/services/knowledge.py) | Linked educational trio retrieval and provenance |
| [report service](src/retail_assistant/services/reports.py) | Explicit report intents, previews/saving/decisions shared by CLI and graph |
| [models.py](src/retail_assistant/models.py), [store.py](src/retail_assistant/store.py) | Local ORM mappings, async session lifecycle, owned state, atomic deletion/receipts and spend reservations |
| [warehouse_sql.py](src/retail_assistant/warehouse_sql.py) | Trusted BigQuery Core schema/projections and native parameter compilation |
| [responses.py](src/retail_assistant/responses.py) | Reply validation and deterministic evidence/limitation rendering |
| [policy.py](src/retail_assistant/policy.py), [warehouse.py](src/retail_assistant/warehouse.py) | SQL compilation/policy versus external BigQuery execution |
| [llm.py](src/retail_assistant/llm.py) | Provider preflight, transport, retry and cost settlement |

Services receive dependencies explicitly; none imports the CLI or LangGraph. SQL
transactions remain together rather than splitting an atomic operation across managers.
Tool confirmation is unavailable: the CLI invokes the report service's explicit action
method, and the store rechecks ownership/frozen hashes inside its transaction.
