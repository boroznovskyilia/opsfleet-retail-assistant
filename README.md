# OpsFleet retail analysis assistant

English CLI built with **LangGraph**, Gemini through OpenRouter and guarded BigQuery.
It investigates permitted completed sales, discusses follow-ups, retrieves educational
analyst methods, saves requested reports and deletes owned reports only after explicit
confirmation. Local safety/process tests run without credentials; real provider/source
checks and their limits are recorded separately.

## Start

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Make. From this checkout:

```sh
make setup
make test
make run
```

`make setup` installs the locked dependencies. Chat requires credentials; report/history
commands remain usable without them. Follow [the integration guide](docs/development/setup.md)
to create `.env` from [.env.example](.env.example), configure a dedicated OpenRouter key
with a **non-resetting USD 5 limit**, and create a Google BigQuery Sandbox project plus
local ADC. No BigQuery API key or billing account is needed for the documented Sandbox
path. No credentials belong in chat/Git. Run the metadata-only readiness check:

```sh
make doctor
```

An unconfigured setup returns clear errors and exit 1, rather than a fake answer.
The code does not perform paid health checks or call a model at startup. Total paid
OpenRouter development/evaluation is capped locally across restarts; uncertain costs
retain their reservations. Provider-side key limit is verified before paid dispatch.

## Example interaction

```text
You> /period 2026-04-01 2026-04-30
You> Compare completed sales and spending per active buyer by state.
You> Investigate whether order frequency or average order value explains the difference.
You> Create a report with findings, hypotheses and actions to validate next month.
You> /reports
You> /delete conversation
... exact owned report IDs/titles, count, and the history-retention notice ...
You> /confirm <action_id_shown_in_preview>
```

This is an example run sequence, not a fabricated live transcript or expected numeric
answer. Live coverage depends on the dataset and five-buyer minimum. Use explicit
periods; unsupported dates/metrics are clarified. Q1 2026 and April 2026 are recognized,
as are last month/quarter. Multiple named periods need one explicit combined date range.

At startup the CLI prints its conversation ID. Resume after restart with:

```sh
.venv/bin/python -m retail_assistant --user analyst_a --thread YOUR_THREAD_ID
```

`/help` lists period/history/report/delete/status commands. `/reject [action_id]`
rejects a preview. A plain conversational “yes” never confirms. Library deletion
**retains chat history and exported copies**; the preview states this explicitly.
`/save TITLE` saves the last assistant answer. Ordinary replies are not autosaved.

Local history, reports, deletion actions and the spend ledger use SQLAlchemy 2 with
aiosqlite. Each operation owns a short AsyncSession; sessions are never shared or kept
open while awaiting Gemini/BigQuery. Existing `.runtime/app.sqlite` files work in place;
do not delete them to upgrade. [Session design](DESIGN.md#persistence-and-sessions).

## Access, privacy and SQL

Two demo identities: analyst_a may analyze even product IDs; analyst_b odd IDs. Select
with `--user`. Login is demonstrative; checks against model-selected data/report access
are real. This is not production multi-user authentication or protection against a
local machine owner editing the files.

The model writes a deliberate flat SELECT subset against logical `sales`. Trusted SQLAlchemy Core code
joins all four required source tables, binds user scope/UTC dates and projects no raw
customer PII. SQLGlot restricts dimensions/metric formulas/filters; code adds the
five-buyer minimum before ordering/limits. Customer ranking is an explicit exception:
pseudonymous ID and amount only. No arbitrary nested SQL, raw tables, write SQL or
functions. Counts/order grain avoid multiplying mixed-product baskets. Numeric
results render in code; LLM interpretations remain subject to source review.

Revenue is completed non-returned item sale prices, not gross ordered sales. All
buyer/order/value denominators share permitted products and period. Monetary labels
use dataset sale-price units pending a verified currency convention. No historical
as-of state or causal identification is claimed. Churn is not a predefined metric.
The cohort threshold and basic free-text redaction are not an anonymity guarantee.

## Architecture and explanations

- [SQLAlchemy migration review](docs/evaluation/sqlalchemy-review.md): sessions, current checks and preserved data.
- [Requirement conformance](docs/evaluation/conformance.md): obligations, checks and evidence limits.
- [Full prototype specification](docs/specs/prototype.md): runtime/data/SQL/tool/action/cost contract.
- [Production HLD](docs/architecture/production.md): Mermaid, concrete services, all eight requirements.
- [Design summary](DESIGN.md): framework/model choices and prototype boundaries.
- [Resourcing comparison](docs/architecture/overview.md): agent, text-to-SQL, RAG and observed traps.
- [Owner decisions](docs/decisions/README.md), [source requirements](docs/specs/requirements.md),
  [original assignment](docs/reference/retail-assignment.txt) and [remaining work](NOT_DONE.md).

Golden retrieval selects IDs from the complete four-method educational catalogue,
then retrieves linked question/SQL/report examples. It needs no embedding key and
never treats old/sample report values as current data. Preferences, learning loop,
editable persona and production services are detailed design only.

## Verification and evaluation

```sh
make verify       # repository tooling + local application tests
make evaluate     # local mechanics report; no paid or cloud calls
```

The suite uses synthetic four-table data, real SQL parsing/compilation, real local
SQLAlchemy/SQLite and async LangGraph, mocked SDK/HTTP boundaries and actual CLI
subprocess restarts. Legacy-state, rollback/cancellation and separate-session/process
races are included.
Test doubles stay under tests/. They establish tested mechanics, not Gemini accuracy
or unseen-question accuracy. [Evidence and limits](docs/development/verification.md).

After credentials are configured, request a real three-case review run explicitly:

```sh
.venv/bin/python -m retail_assistant.evaluation --live --start 2026-04-01 --end 2026-04-30
```

It shares the same cumulative USD 5 ledger, preserves responses/evidence under
`.runtime/evaluation/`, and exits 2 because free-text correctness requires review.
It does not assign a fake automatic accuracy score. Recorded real integration/source reviews are linked in
[verification](docs/development/verification.md). Verify numeric results independently and review intent, hypotheses,
actionability, access boundaries and UX before claiming acceptance.

Local metadata-only JSON traces rotate in `.runtime/events.jsonl`; outputs include
request IDs, SQL/job fingerprints, errors, token/cost/scan metrics and action receipts.
No raw prompts/results, API keys or secret bindings are logged. Owned full history
and reports live in `.runtime/app.sqlite`. Keep the ledger/state when resuming work.

## Development harness

The original 21-file harness came from template_proj commit e4b237b8b0bb95ec292207bcd77fdbb6aa245e36,
exported while preserving this checkout's `.git`. The four validator/test scripts
and generic workflow remain; Makefile/.gitignore and product docs now support this app.
No staffing source, secrets, runtime files or completed-task history were imported.
Use `make docs`, `make progress` and [AGENTS.md](AGENTS.md) to resume. The harness does
not run an agent in the background. Publication details are recorded in [progress](docs/plans/progress.json). Production
infrastructure is not deployed.
