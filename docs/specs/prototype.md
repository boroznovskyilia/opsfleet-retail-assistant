# Prototype contract

This is the implementation contract derived from the original assignment and
DEC-01 through DEC-23. Accepted choices live in the decision register; numerical
limits below are engineering defaults. Production-only features are in the
[production HLD](../architecture/production.md). No live data/model quality is implied.

## Runtime and interface

Python 3.12+, LangGraph, SQLGlot, httpx, SQLAlchemy 2/aiosqlite, sqlalchemy-bigquery,
google-cloud-bigquery and python-dotenv.
CLI only; one local process/worker. SQLite stores independent owned conversations,
reports, immutable deletion previews/receipts and cumulative model-spend reservations.
LangGraph controls the model/tool loop; the app reloads bounded completed chat history
for each turn. Mid-turn graph execution is not checkpoint-resumed after a crash;
completed history and pending deletion actions survive restart. No API/React/DSPy.

Database access uses SQLAlchemy ORM/Core expressions. Each Store operation owns a
fresh AsyncSession and transaction; never share a session between tasks or retain it
across model/warehouse calls. Context managers commit on success, roll back on errors
or cancellation, and close the session. Engine disposal occurs on CLI/evaluation exit.
SQLite write transactions take BEGIN IMMEDIATE before the initial check so exact-set
deletion and spend reservations stay atomic across connections/processes. Existing
column names/JSON formats and all durable state remain compatible without a reset.

The BigQuery source projection and product catalogue use SQLAlchemy Core plus the
Google-maintained dialect. The generated/validated analytical SQL still executes
through the native BigQuery SDK for dry runs, scan caps, deadlines and job cancellation;
its synchronous calls run in a worker thread. The agent graph uses ainvoke and model
transport uses AsyncClient. Required text-to-SQL, its policy expressions/examples,
independent source-oracle SQL and SQLite BEGIN statements remain intentional SQL.

English is tested. A CLI user selector chooses analyst_a (even product IDs) or
analyst_b (odd IDs). This is an explicitly disclosed demo login, not authentication.
User/grants are server-owned and cannot be model tool arguments. Production must use
real identity and entitlements. No cross-user or cross-thread conversational memory.

## Data and metrics

Source is bigquery-public-data.thelook_ecommerce. Trusted code joins order_items to
orders by order_id (and consistent user_id), products by product_id, users by user_id.
One item is one fact. Admit orders/status Complete and items/status Complete, with no
returned_at. Sale time is order_items.created_at UTC; monetary source is sale_price
cast to NUMERIC. Required fields and qualifying sales were verified by metadata and bounded live reads;
fail clearly on future schema drift instead of guessing. Currency is labeled dataset sale-price
units until a verified USD convention exists; do not invent FX or currency metadata.

The model sees a logical `sales` relation: sale_date, product_id, product_name,
category, brand, department, state, country, customer_ref, order_id, item_id, amount.
Underlying PII columns are never projected. The relation is already filtered to the
current user's product parity and selected inclusive date range, converted to UTC
[start, next day after end). Customer references are secret-salted, user-scoped hashes;
the secret is local and never sent to the LLM, SQL evidence bindings or logs.

Active buyer: DISTINCT customer_ref with a qualifying item; order count: DISTINCT
order_id within that same permitted cohort. A mixed-product order contributes only
permitted item amounts and one qualifying order. Revenue SUM(amount); average order
value SAFE_DIVIDE(revenue, orders); order frequency SAFE_DIVIDE(orders, buyers);
spend per buyer SAFE_DIVIDE(revenue, buyers). Decomposition holds at the same grain.

Time-dependent reads require an explicit period or a previously established period
in the same thread. No silent last-month default. `/period START END` is authoritative;
recognize ISO ranges, named month+year, Q1-Q4+year and common relative month/quarter
expressions deterministically. Unsupported/ambiguous natural periods are clarified.
Schema/catalogue reads need no period. Churn is not a predefined metric: clarify its
inactivity/cohort definition and disclose the prototype metric limitation.

## SQL trust boundary

The model generates a single flat BigQuery SELECT FROM sales, with allowed dimensions,
approved aggregate formulas/aliases, literal filters, GROUP BY, ORDER BY and LIMIT.
No scripts, DML/DDL, CTEs, subqueries, joins, UNION, windows, external functions,
raw datasets, private columns, arbitrary projections or model-written HAVING.
SQLGlot parses structure; code validates each clause and compiles it against the
trusted scoped source relation with bound period/parity/secret parameters. Literals
remain AST-serialized data, never concatenated unchecked. This deliberate subset
supports the enumerated sales/customer/product/time examples via multiple queries;
unsupported analyses clarify rather than pretending to be unrestricted SQL.

Group dimensions are product/category/brand/department/state/country/date and approved
month/quarter/year buckets. Numeric metrics are computed by BigQuery. Code adds
COUNT(DISTINCT customer_ref)>=5 before ordering/limits. Never trust an LLM support
count. Customer ranking is a separate shape: only customer_ref plus SUM(amount),
GROUP BY customer_ref, no personal attributes. The explicit ranking exception is not
anonymous reporting. The threshold is not differential privacy or inference prevention.

100 display rows, 101-row sentinel, bounded payload; explicit truncation/top-N metadata.
Dry run before execution; maximum_bytes_billed=256 MiB/job, 1 GiB/turn reservation;
up to four analytical queries/turn. Scan limits differ from output limits. Deadlines
and cancellation are best effort at the provider; do not claim cancellation reverses
charges. Database schema checks use metadata only and do not read PII values.

## Agent and RAG

One LangGraph loop alternates model decisions and controlled tools: schema/catalogue,
Golden retrieval, sales SQL, owned report listing and deletion preparation. No model
can confirm deletion. Server-derived period, identity, grants and counters are exact
state outside model prose. Tools return typed bounded evidence/error codes. Preserve
Google/OpenRouter-required tool-call metadata only within the current turn; do not
expose private reasoning or save raw transport bodies in ordinary history/logs.

Six model calls, eight tool calls, four SQL reads and a 60s turn deadline. Reserve
the last model call for tool-free final composition; exhausted research may still
produce a grounded report with explicit missing coverage and proposed validation. A call uses
at most 24 KiB rendered JSON input and 1500 completion tokens; drop old complete turns
before optional evidence samples, never the latest input/policy. Exact results remain
available in history/reports. Interpretations receive the first eight rows of each
query and disclose that sample when larger tables are displayed; global claims need
separate source evidence. On exhaustion return deterministic verified tables and
explicit missing parts. No result is an ordinary outcome; one diagnostic correction
may fix syntax/schema/format, never permissions or relaxed user filters. One transient
HTTP retry (429/5xx/transport) within deadline; one shared invalid-output/SQL correction.
No raw provider exception text in UI/logs. Missing credentials fail clearly, no canned
production answers. UI keeps working and deterministic report commands remain available.

Golden demo: 3-5 clearly labeled educational trios, not reference answers. Retrieve
relevant method IDs by bounded semantic model selection over the complete small
catalogue; validate IDs, return linked method/SQL/report and never execute sample SQL.
No embedding credential/service required. Empty relevance is explicit. Production
replaces this tiny-corpus scan with ACL-filtered hybrid retrieval and reviewed updates.

Model explanations distinguish measured factors, hypotheses and proposed validation.
Only successful query evidence is shown as numerical proof; tool success does not
prove semantics. Tables render in code even if prose generation fails. A report is
saved only on explicit create/save request or `/save`, with its evidence/period/scope.
For a requested report, a completed model analysis requires current evidence IDs and
at least one proposed action; a missing field uses the same single output-repair
allowance. If composition fails, preserve verified partial evidence with limitations.
Report source text is untrusted data. Direct database PII is excluded by projection;
basic redaction additionally covers obvious PII in user/model free text, but is not a
complete named-entity detector or a general anonymization guarantee.

## Reports and destructive confirmation

Library records have owner, thread, stable ID, creation time and content hash. Plain
answers stay history. Search all owned titles/bodies using Unicode case-insensitive
literal phrase matching, no alias inference; reject empty phrase. Current-conversation
selection additionally binds thread ownership. Natural-language deletion prepares
only; explicit CLI commands can also prepare a phrase/thread deletion without LLM.

Persist exact report IDs/hashes and an action ID before preview. Explain that chat
history and exported copies are not erased. `/confirm ID` atomically rechecks owner,
thread, pending state and hashes, deletes the exact set and saves a receipt in the
same SQLite transaction. New matches after preview are excluded; changed/missing
previewed reports cause a stale conflict and no deletion. Repeated same decision
returns its receipt; opposite/stale/cross-user decisions fail. `/reject [ID]` deletes
nothing. A replacement preview supersedes the old action. Read chat can continue while
pending. Restart restores action/receipt; no LLM needed for confirmation or recovery.

## Cost and observability

USD 5 cumulative across paid development/evaluation calls and restarts. Never reset
for a new turn. Reserve a conservative upper bound atomically before each physical
attempt; reconcile only with verified provider usage cost. Unknown cost leaves the
reservation charged. Crash reservations remain charged. A dedicated provider key
must also have a non-resetting <=USD 5 credit limit before live calls. Price ceilings,
input/output caps and provider parameter requirements prevent silently routing to an
unbounded model. No paid health probes or automatic startup model calls.

JSON logs: request/thread/user reference, stage, attempt, latency, SQL fingerprint,
BigQuery job/scan counts, result/truncation, policy/error codes, tokens/cost and action
receipt IDs. No API keys, secret bindings, raw prompts, free text or result rows.
Bounded rotating local files. Full user-visible history/evidence is owned SQLite data,
not ordinary telemetry. Production metrics/alerts/retention are in the HLD.

## Acceptance and verification

| Scenario | Observable assertion | Check location |
| --- | --- | --- |
| SQL policy/PII | Reject writes, alternate relations, scripts/CTEs/subqueries/functions/private projections; scope always injected | tests/test_policy.py |
| Metric scope | Distinct buyers/orders, item grain, mixed products, zero/empty and month boundaries | tests/test_policy.py, tests/test_agent.py |
| Cohort privacy | Code adds threshold before LIMIT; individual ranking only ID+amount | tests/test_policy.py |
| Confirmation | Preview unchanged data; exact owned set; Reject/repeat/stale/concurrency/restart | tests/test_store.py |
| Budget | Atomic reservations, retries/crash/unknown cost cannot bypass USD 5 | tests/test_store.py, tests/test_llm.py |
| Async persistence | Legacy rows/aliases/budget preserved, separate sessions, rollback/cancellation, no checked-out connection across HTTP/warehouse, engine disposal | tests/test_store.py, tests/test_llm.py, tests/test_services.py, tests/test_process.py |
| Agent | Real LangGraph with scripted test transport: iterative reads, missing period, fallback, report save | tests/test_agent.py |
| Real integration | Metadata, dry-run/bounded read, actual Gemini tool loop/report quality | --doctor, live evaluation and independent source review; see verification |

Test doubles are confined to tests; fixtures are synthetic and prove mechanics, not
BigQuery/model correctness. Preserve failed outputs and report actual live results.
No assertion of unseen-question accuracy or production readiness follows from local
passes. Performance is measured rather than inferred from the 60s target.
