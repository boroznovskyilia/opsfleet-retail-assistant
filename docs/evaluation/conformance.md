# Requirement conformance and acceptance evidence

Scope is the original assignment plus DEC-01 through DEC-23: a working CLI prototype,
all production requirements in the HLD, and four educational Golden trios in runtime.
Design-only requirements are evaluated as design deliverables. This matrix identifies
what a passing check proves; it is not a universal correctness or privacy guarantee.
Executed results and source fingerprints are in [verification](../development/verification.md).

| Obligation | Implementation/design | Acceptance evidence |
| --- | --- | --- |
| CORE-01/05: dynamic SQL over the four BigQuery sources | [Compiler](../../src/retail_assistant/policy.py), [warehouse](../../src/retail_assistant/warehouse.py), [analysis service](../../src/retail_assistant/services/analysis.py) | Synthetic four-table metric oracles and real compiled query; live question results reviewed separately |
| CORE-02: follow-up discussion | Explicit thread period, owned bounded completed history, repeated research | [Agent tests](../../tests/test_agent.py), [CLI process tests](../../tests/test_process.py); real CLI follow-up recorded in the live review |
| CORE-03: requested report with insights/actions | Validated evidence IDs/actions, final composition call reserved, explicit saving | Agent regressions for missing actions, shared repair and final-call/query-budget exhaustion; live report review |
| CORE-04: explain available data | Safe schema/metric catalogue and permitted product sample | Schema/catalogue graph scenario and warehouse metadata check |
| REQ-01: hybrid intelligence | [Golden service](../../src/retail_assistant/services/knowledge.py), [reviewed corpus/index design](../architecture/production.md) | Four labeled linked trios compile; unknown/empty selections checked; real methodology retrieval in live traces |
| REQ-02: scope, malicious requests, PII and products | Trusted owner/parity/period binding; allowed AST surface; PII columns excluded before model; five-buyer grouping rule and explicit ranking exception | [Policy attacks/cohort oracles](../../tests/test_policy.py), source PII canaries in agent tests, cross-owner storage/process scenarios; real odd/even scoped reads |
| REQ-03: owned destructive actions with confirmation | [Report service](../../src/retail_assistant/services/reports.py), frozen ID/hash selection, atomic receipt, /confirm ID | [Store tests](../../tests/test_store.py): race/retry/stale/opposite/ownership/literal matching; real CLI restart/confirm retains history; negated intent cannot prepare |
| REQ-04: user preferences and system learning | Owned versioned preferences, reviewed feedback/trio release pipeline | [Production HLD](../architecture/production.md); design-only as agreed, no self-learning runtime claim |
| REQ-05: recovery and costs | Shared single syntax/output correction, empty-result diagnostics, bounded transient retry, time/scan/payload/query budgets, conservative cumulative reservations, partial evidence | Agent/service/HTTP/SDK regressions; expired metadata makes no external request; actual provider routing failure retained and fixed; live timings recorded |
| REQ-06: agent/report/intent/UX QA | [Evaluation runner](../../src/retail_assistant/evaluation.py), source calculations, adversarial suite and executive-task design | Local results, real output/source review and process acceptance; independent human/held-out UX studies remain future production validation |
| REQ-07: observability | Correlated user/thread/request/query/job metadata, model tokens/cost/HTTP status, tools/repair/partial/action events; owned history separate from logs | Missing-provider actual process check; metadata contains no prompt/PII/key; actual live job/model correlation retained in private runtime evidence |
| REQ-08: editable persona without redeploy | Authenticated versioned admin editor, preview/evaluation, activation/cache and rollback | Production HLD; design-only, never overrides immutable policy |
| DEL-01/02: diagram/services/flows/reasons/all eight requirements | [Production HLD](../architecture/production.md), [DESIGN](../../DESIGN.md), [prototype contract](../specs/prototype.md) | Manual source-to-design consistency review; no production hosting claim |
| DEL-03: CLI, setup and another machine | English CLI, locked Python package, [README](../../README.md), [setup](../development/setup.md) | Clean export locked installation/build, package includes Golden JSON, real subprocess restart |
| DEL-04: framework choice and honest experience | LangGraph selected by owner; hands-on implementation with AI assistance | DESIGN explains selection and assistance; no invented experience tenure |
| DEL-05: public repository submission | [Public GitHub repository](https://github.com/boroznovskyilia/opsfleet-retail-assistant) with source, docs and Mermaid architecture | Anonymous public access and exact remote/local file hashes verified; commit details are tracked in [progress](../plans/progress.json). Sending the link to the hiring team is separate |

## Accepted refinements

The suite checks explicit-period clarification/reuse; common allowed product cohort
for spend/frequency/AOV; five-buyer suppression before LIMIT; ranking restricted to
pseudonym+amount; own reports matched by case-insensitive literal title/body text;
no aliases; immutable confirmation and retained history; ordinary chat never autosaves;
unknown costs survive restart and the USD 5 cap is cumulative. Two identities are demo
selection, not production authentication. See [decisions](../decisions/README.md).

DEC-23 adds SQLAlchemy/aiosqlite persistence with one session per operation, Core-built
trusted warehouse queries, async graph/model/service callers and unchanged durable
formats. Store/HTTP/process tests cover legacy files, separate-session concurrency,
rollback/cancellation, resource return, exact deletion/receipt atomicity and the shared
spend cap. Current rewrite evidence is in the [SQLAlchemy review](sqlalchemy-review.md);
earlier live results remain tied to their recorded source versions.

## Limits that remain visible

SQL is a documented flat grouped subset; arbitrary joins/windows/custom churn and
causal identification are unsupported. Free-text redaction is basic; the primary
source PII boundary is projection. Five-buyer suppression and pseudonyms do not prove
anonymity or prevent inference attacks. Explanations receive eight sampled rows per
query and must not infer global coverage from that sample. Current source values are
mutable; retained results and timestamps matter. Production load, independent expert
review and executive UX testing have no passing empirical claim here.
