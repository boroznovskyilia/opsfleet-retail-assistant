# Source catalogue

Inspected on 2026-11-02. The initial request authorized analysis, documentation and
harness transfer. A follow-up requests an architecture review and full vision interview,
then specification and implementation. Publishing and external messages remain separate.

## Inputs and authority

| ID | Input | Authority and limits |
| --- | --- | --- |
| SRC-O | Owner's initial chat request | Analyze Resourcing assignment, approach and corner cases; copy template harness here; explain OpsFleet differences, especially agent, text-to-SQL and RAG |
| SRC-V | Owner's follow-up request and interview answers | Evaluate architecture and conduct a thorough vision interview, then specification and implementation; accepted direction is recorded in product core |
| SRC-R | [Original retail assignment](retail-assignment.txt) | Original OpsFleet obligations; preserved byte-for-byte from the pasted attachment |
| SRC-C | User-pasted db_client.py | Starter BigQueryRunner only; described below; no runnable application was supplied |
| SRC-S | Local resoursing_assistant_test checkout | Comparison evidence: original DOCX, accepted requirements/decisions, actual runtime paths, tests and recorded evaluation; not a source of OpsFleet requirements |
| SRC-T | Committed template_proj harness | Generic development tooling/workflow; selects no application stack or product behavior |

Retail attachment SHA-256:
`8612bea341dc13810b52e77477b90540eb141bd953160b3b929db144785b4826`.

## Resourcing inspection provenance

Local path: `/Users/iliab/projects/resoursing_assistant_test`, HEAD `dbde03b`.
Existing uncommitted edits to `docs/plans/implementation.md` and
`docs/plans/progress.json` were left intact. The published evaluation refers to
runtime `23487e3`; later documentation commits are not new model runs.

Read the original `docs/reference/assignment-brief.docx` text, dictionary, ten gold
and twelve additional questions; the product, architecture, requirements, agent,
retrieval, data, booking, operations and evaluation evidence. Checked the implementation
in `agent/graph.py`, `agent/reads.py`, `agent/read_policy.py`, `db/reader.py`,
`services/retrieval.py`, `services/documents.py`, `services/bookings.py`,
`db/bookings.py`, `llm/signatures.py`, configuration and telemetry, plus relevant
test inventories and retained failure artifacts. This is targeted architecture/source
review, not an exhaustive defect audit of every function or frontend file.

Read-only checks against bundled `data/source.sqlite` independently confirmed 24
tables, 34 duplicated display names affecting 68 people, 2,095 mismatched booking vs
allocation person references, 373 risk rows with ten unique descriptions, and
508,554.3 all-level versus 169,518.1 leaf work hours. The source fingerprint matched
`8d00b91ae6aa23bbcf0d807c2e51fa6a45f7017a6557a4f51d11cfc82bfb4259`.

Neighbor paths are inspection provenance only. This repository's checks and documents
work without those repositories; no credentials or runtime databases were copied.

## Starter client facts

The supplied BigQueryRunner creates a `google.cloud.bigquery.Client`, stores a dataset
name, executes caller-provided SQL and returns a pandas DataFrame; it also retrieves
one table's schema and logs operations/exceptions. Its dataset field only qualifies
schema lookups, not SQL execution. It contains no LLM, SQL policy, product authorization,
PII control, retry/repair, saved reports or trace context. Read-only access depends on
external permissions; the class does not establish it.

At the initial inspection, the client code was read as pasted text; no dependencies
were installed or queries executed. Public BigQuery schemas/data and account quota were not checked
live. During the vision interview, official docs/catalogues were checked for Sandbox
allowance, ADC authentication, client cost-limit configuration and Gemini availability
through OpenRouter. Sources and prerequisites are in [setup](../development/setup.md).
Catalogue/documentation checks alone are not authenticated model/data smoke tests.
Subsequent actual setup, bounded source/model checks and spend evidence are recorded
in [verification](../development/verification.md).

## Harness provenance

Source path: `/Users/iliab/projects/template_proj`, commit
`e4b237b8b0bb95ec292207bcd77fdbb6aa245e36`. Exported its 21 tracked files into the
existing checkout, retaining destination Git identity and excluding source history,
working changes and credentials. At import, generic scripts/Makefile/workflow were
unchanged; project documents and authorization/task state were initialized from SRC-O/SRC-R.
During implementation, Makefile/.gitignore gained app commands/runtime exclusions;
the four validator/test scripts and generic workflow remain unchanged.

## Unresolved meaning

Open application-policy questions belong in [requirements](../specs/requirements.md).
Resolve material questions through the vision interview before dependent specification
or implementation. Never silently resolve them using the staffing application's
accepted choices or its gold expected answers.
