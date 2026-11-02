# Requirements and corner cases

Source obligations from [the preserved assignment](../reference/retail-assignment.txt)
and accepted owner refinements. Detailed behavior is in [the prototype contract](prototype.md);
implemented checks and remaining live limits are in [verification](../development/verification.md).

## Required core and deliverables

| ID | Obligation | Required delivery |
| --- | --- | --- |
| CORE-01 | Natural-language retail analysis with dynamically constructed and executed SQL | Working prototype |
| CORE-02 | Follow-up conversation about the data | Working prototype |
| CORE-03 | Generate a report with insights and action items when requested | Working prototype |
| CORE-04 | Explain the available database structure and supported analyses | Expected agent capability |
| CORE-05 | BigQuery dataset bigquery-public-data.thelook_ecommerce; orders, order_items, products, users | Working integration |
| DEL-01 | Architecture diagram with components, services/compute, stores and communication | Design |
| DEL-02 | Detailed explanation of cloud/model/framework choices, all eight requirements, flows and fallback | Design |
| DEL-03 | CLI chat, documented setup and example run on another machine | Working prototype and README |
| DEL-04 | Use a framework; explain its choice and personal experience | Implementation and explanation |
| DEL-05 | Public GitHub repository with documentation, source and architecture | Submission |

Gemini is preferred, not stated as mandatory. Docker is explicitly optional. Graphs,
mail and web trends illustrate extensibility; their implementation is not required.
The original text's pricing/free-tier claims are not verified current pricing.

## Eight cross-cutting requirements

| ID | Requirement | Design | Prototype |
| --- | --- | --- | --- |
| REQ-01 | Hybrid intelligence from historical expert question/SQL/report trios; update and query-time retrieval | Required | Not in the mandatory four |
| REQ-02 | Analytics-only scope, malicious-user safeguards, no final-output PII, product-level user restrictions | Required | Required |
| REQ-03 | User-owned saved-report deletion by content or current conversation; strict confirmation with usable UX | Required | Required |
| REQ-04 | Learn user presentation/depth preferences and improve the system from interactions | Required | Not in the mandatory four |
| REQ-05 | Detect SQL syntax errors/empty returns, bounded self-correction, graceful API/service failure and cost control | Required | Required |
| REQ-06 | Predeployment agent, intent/report correctness and UX evaluation | Required | No prescribed runnable evaluation suite |
| REQ-07 | Agent metrics, failure causes and deep-dive message/tool correspondence | Required | Required |
| REQ-08 | Non-developer changes to tone/instructions without redeployment | Required | Not in the mandatory four |

The four-item list narrows required prototype cross-cutting features; it does not
remove CORE-01/02/03, the BigQuery integration, CLI or reproducibility. Basic report
storage and ownership are needed to demonstrate deletion. The Golden Bucket is
explicitly theoretical; no actual corpus was supplied. Do not describe it as present.
DEC-14 adds a small explicitly educational runtime corpus and retrieval demo to the
owner-selected prototype scope; it does not turn sample data into supplied golden
knowledge. Preferences, learning and persona remain design-only.

## Corner cases to settle and test

These are proposed acceptance scenarios, not extra source mandates or executed tests.

| Area | Case | Required property or proposed safeguard |
| --- | --- | --- |
| User identity | Application user is confused with a customer in users | Separate application identity and server-owned product grants |
| Authorization | A prompt asks to ignore restrictions or aggregate another user's products | Apply allowed-product scope before aggregation; a prompt is no authorization boundary |
| Authorization | A query uses aliases, CTEs, subqueries or another dataset to bypass filters | Validate actual accessible relations and enforce scope on every source path |
| Authorization | An allowed user's access changes during a conversation or before deletion | Revalidate current grants/ownership at execution; do not trust remembered permissions |
| Privacy | User requests top customers or a singleton aggregate | Resolve permitted identifiers and small-group policy; avoid direct PII; small groups can permit inference |
| Privacy | Data appears in SQL literals, exception text, report preview, logs, history or retrieved examples | Keep sensitive values out of ordinary telemetry; protect all storage/retrieval/output paths |
| Golden knowledge | Similar historical example uses old schema, a different metric, period or product scope | Use validated versioned methodology; regenerate/revalidate SQL and rerun current facts |
| Golden knowledge | Report text contains injected instructions or cross-user data | Retrieved text is evidence, never authority; filter permitted corpus before retrieval |
| Golden knowledge | No suitable example is found | Declare missing method or use an approved fallback; never fabricate historical support |
| SQL grain | Orders join to items; customer rows and order rows repeat | Choose result grain; avoid multiplying totals or dropping zero-activity entities |
| Metrics | Revenue could mean gross orders, completed sales or net of returns | Define formula, statuses, date field, units and denominator before claiming a result |
| Metrics | Churn is requested without an inactivity window/cohort | Clarify or disclose an explicit metric definition; it is not automatically a stored field |
| Time | Last month/current quarter, timezone, incomplete month or reference date ambiguity | Resolve explicit bounds and comparison periods; compare compatible windows |
| Explanation | Lower spend may reflect customer mix, frequency or basket size | Decompose observed metrics; distinguish descriptive evidence from causal hypotheses |
| Recovery | Valid empty result versus bad date/status/name interpretation | Diagnose safely; one meaningful correction preserves intent; do not relax filters to find a match |
| Recovery | 429, timeout or provider outage; SQL safety rejection | Bounded transient retry; policy rejection remains final; retain useful verified results |
| Cost | LIMIT 10 over an expensive scan or a huge DataFrame | Separate scan/cost budgets from result row/byte limits and deadlines |
| Deletion | All reports mentioning Client X, including paraphrases | Define matching semantics and examine the full owned scope; top-k alone cannot prove all |
| Deletion | Zero, one or many matches, mixed ownership or an ambiguous client name | Show a safe scoped preview/count; clarify ambiguity; never include foreign-owned reports |
| Deletion | Reports change after preview; a new report later matches the phrase | Bind confirmation to a stable reviewed set/version; do not silently expand it |
| Deletion | Repeat confirmation, stale action, restart, concurrent decisions or lost response after commit | Fixed idempotent action, stored terms, ownership recheck and durable receipt |
| Memory | Preference or summary says to bypass privacy or delete without asking | Preferences cannot override authorization, privacy or confirmation rules |
| Persona | Weekly tone update introduces unsafe instructions | Versioned presentation instructions remain subordinate to fixed safety rules |
| Learning | Positive feedback on an incorrect answer | Feedback is a review signal; do not auto-promote it into trusted golden knowledge |
| Observability | Logs look successful but the SQL answered the wrong metric | Track factual/semantic evaluation separately from execution success |

## Owner-selected baseline

The [product core](../product/core.md) and [decision register](../decisions/README.md)
record accepted scope, analytical focus, ambiguity handling, sales/spending basis and
two-user demo identity, privacy direction and factual/hypothetical explanation boundary.
These refine the assignment without replacing it. Local checks cover the mapped
prototype scenarios; actual BigQuery source mapping is still unverified.

## Resolved choices and remaining verification

The interview's essential policy choices are recorded in the decision register.
The [prototype contract](prototype.md) specifies the two parity-based demo grants,
PII-free projection and pseudonym derivation, five-buyer enforcement and ranking
exception, shared metric cohort, explicit periods, immutable owned report selection,
atomic confirmation/receipts, educational trios and numerical research/cost budgets.
The [production HLD](../architecture/production.md) defines trusted identity,
corpus approval, preferences, persona and production operations separately.

A valid empty or suppressed result is returned to the analytical loop for diagnosis.
A subsequent query must preserve the user's intent and all access/privacy rules;
there is no blind rerun or weakened threshold just to obtain rows. Syntax/output
correction shares one bounded allowance. This is an engineering recovery default,
not a claim that an empty result always indicates a query error.

Actual status/date/currency/source freshness mapping and Gemini interpretation,
empty-result diagnosis, latency and report quality need live verification. The source
schema assumptions remain provisional until doctor and bounded queries succeed.
Missing user-local credentials block those checks. Current status and the next
concrete action belong in [progress.json](../plans/progress.json).
