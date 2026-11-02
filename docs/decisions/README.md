# Decisions

Create a decision record when, without the recorded reason, a future team would
likely repeat the same debate or accidentally violate a constraint.

Name the file after the topic, such as `database-choice.md`. Include the context,
decision, alternatives considered, consequences, and status.
State which earlier decision it supersedes. Do not log every agent action here.

LangGraph was owner-selected; the prototype uses BigQuery, Gemini/OpenRouter,
SQLGlot, httpx, SQLAlchemy/aiosqlite, SQLite and dotenv. Reasons and restrictions are in the
[prototype contract](../specs/prototype.md), independently of the comparison project's stack.

## Initial analysis scope

The owner's initial 2026-11-02 request authorized source analysis, a Russian explanation and
copying the template_proj harness into the existing repository. Exporting the committed
files preserves destination Git identity and avoids importing credentials, source
working changes or another project's completed-task history. The source commit is
recorded in the [catalogue](../reference/README.md).

The comparison's retail flow and safety mechanisms are recommendations, not accepted
answers to the outstanding business-policy questions. That initial request did not
include application implementation, publishing or messages to third parties.

## Follow-up scope and initial vision

The owner subsequently requested architecture evaluation and a thorough vision
interview, followed by specification and implementation. This supersedes the initial
analysis-only work boundary; it does not waive the requested vision-first sequence
or authorize publishing/external messages. Continue to implementation once its agreed
vision and specifications are concrete, without a repeat blanket start approval.

### Accepted vision decisions

The choices below were explicitly selected by the owner on 2026-11-02.

| ID | Decision | Reason and consequence |
| --- | --- | --- |
| DEC-01 | Strong take-home submission within original assignment scope | Prioritize required prototype behavior and production explanation over optional features |
| DEC-02 | Flagship comparison of sales/spending with factor analysis | Demonstrate an investigation and evidence, rather than only query execution |
| DEC-03 | Clarify material ambiguity and disclose safe assumptions | Avoid both unnecessary questioning and silently choosing a materially different metric |
| DEC-04 | Primary comparison metric is spending per active buyer; decompose frequency and average order value | Total revenue alone mixes customer count and individual spending; the shared cohort/grain is defined in the prototype contract |
| DEC-05 | Sum item sale prices for completed orders; exclude cancellations and returns | Explicit sales basis; verify actual source statuses/date/grain before generating runtime SQL |
| DEC-06 | Two predefined CLI users with different product grants; real access enforcement | Keep demo login small while demonstrating the mandatory product boundary; production identity remains a separate HLD concern |
| DEC-07 | Permit aggregates and pseudonymous customer references; do not send names, email, addresses or other direct PII to the model | Enforce the input boundary as well as final-output privacy; field mapping and alias generation need a data contract |
| DEC-08 | Suppress metrics for groups with fewer than five customers and offer a broader selection | Educational privacy rule, explicitly not an anonymity guarantee; intersection with individual customer ranking is unresolved and no exception is assumed |
| DEC-09 | Separate measured explanatory factors from hypotheses; recommendations state how to verify them | Observational comparisons must not be presented as proven causes |
| DEC-10 | Group slices retain the five-customer threshold; individual customer ranking is an explicit exception allowing only pseudonymous ID and amount, without personal attributes | Resolves the open intersection in DEC-07/08; this is a deliberate disclosure policy, not a claim of anonymity |
| DEC-11 | Save a report only on an explicit request to create/save one | Ordinary analytical answers remain conversation history, not automatically saved reports |
| DEC-12 | Confirmed deletion removes a report from the library while preserving conversation history; explain this before deletion | Library deletion is not erasure of previously delivered chat content; do not silently promise broader deletion |
| DEC-13 | Confirm/reject deletion through explicit CLI commands /confirm <action_id> and /reject | Bind the decision to a persisted previewed action; ordinary affirmative chat is not authorization |
| DEC-14 | Include a small clearly educational Golden corpus of 3-5 question/SQL/report trios with working retrieval; keep preferences, learning loop and persona in design only | Demonstrate the central hybrid-intelligence idea without importing a real corpus or expanding all optional runtime features; never present sample trios as human-approved production knowledge |
| DEC-15 | Match the supplied phrase in owned report title/body without case sensitivity; do not automatically equate aliases such as CX and Client X | Owner selected after examples; deterministic full-library search with an explicit preview avoids introducing semantic entity inference into deletion |
| DEC-16 | Agent chooses subsequent read-only research queries within code-enforced budgets, shows concise progress and clarifies material ambiguity | Allows evidence-driven investigation without asking approval for every safe read; policy/actions remain code-owned |
| DEC-17 | Target up to one minute for complex analysis; on budget exhaustion return verified partial findings and offer continuation | Latency is a design target pending measurement, not an SLA; do not fabricate a complete answer |
| DEC-18 | Ask for the period before analytical queries if it is not specified | Do not silently choose a last-month/90-day window; metadata/schema discovery is not a time-dependent sales query |
| DEC-19 | Active buyer has at least one qualifying completed order in the selected period and permitted product scope; all spending/frequency/basket components use that same scope | No buyer denominator or full-basket amount from forbidden products; explicitly define mixed-product order handling in the data contract |
| DEC-20 | Authorize at most USD 5 cumulative paid OpenRouter calls for development and evaluation; stop at the limit | This is a total budget, not a per-run or resetting allowance; key setup/funding stays local with the owner |
| DEC-21 | Use LangGraph | Owner selected the framework; exact personal experience/seniority was not supplied and must not be invented |
| DEC-22 | English is the primary CLI/report/demo language | Test English; repository documentation is English and owner discussion remains Russian |
| DEC-23 | Use SQLAlchemy for database access, prefer async sessions, remove avoidable handwritten SQL | Explicit owner follow-up; supersedes native sqlite3 access. Preserve existing data and safety/cost semantics; retain required guarded text-to-SQL and SQLite transaction-control statements |

DEC-10 resolves the prior customer-ranking/group-threshold question; DEC-15 resolves
report matching after clarification. Detailed data mapping, numeric per-request limits and live
integration setup remain open. Owner selection
of a demo identity model is not authorization to let a prompt select arbitrary grants.
DEC-16 accepts bounded research autonomy and DEC-21 selects LangGraph. Numeric
per-request limits remain engineering work; no comparative superiority claim is made.

### Prototype engineering choices

Use one async LangGraph model/tool loop, httpx AsyncClient for OpenRouter, and local
SQLite through SQLAlchemy AsyncSession/aiosqlite for owned history/reports/actions/spend
reservations. DEC-23 replaces the initial native sqlite3 persistence implementation. Do not require DSPy, React,
FastAPI, a hosted vector service or additional agents. Retrieve from 3-5 educational
methods by bounded model selection over the complete tiny catalogue, using the same
LLM key; no embedding credential is required. This scales only to a small corpus.

Generate flat grouped SELECTs against a logical sales relation. Trusted code builds
that relation from all four source tables, scopes products before aggregation and
excludes PII. A SQL AST policy restricts dimensions, predicates and metric expressions;
code adds support-count suppression before ranking/limits. Individual customer ranking
is a separate restricted shape. This deliberate SQL subset covers the prototype's
enumerated analysis types; nested arbitrary SQL is not supported. See the detailed
[prototype contract](../specs/prototype.md) for enforcement, limits and checks.

### Integration engineering default

The owner has offered OpenRouter access for Gemini. The setup guide proposes a pinned
`google/gemini-3.8-flash` model, listed in the provider catalogue with tools and
structured outputs as checked on 2026-11-02. Start BigQuery with Sandbox and local ADC,
without enabling billing. See [setup and sources](../development/setup.md). These are
configuration recommendations, not successful live checks. DEC-20 supplies the
cumulative spend limit; configure a project-specific key with a non-resetting USD 5
credit limit as an additional provider-side boundary.

## Changes and scope

Use the [human-decision boundary](../development/workflow.md#human-decisions).
Agents may correct stale documentation or resolve technical details inside agreed
behavior independently; unresolved requirement meaning and proposed business changes
need the owner. An explicit owner instruction can already resolve the decision.

Mark replaced choices as superseded and link the active rule/replacement. Keep live
tasks, questions and blockers in [progress.json](../plans/progress.json), not here.
Template workflow conventions do not select product behavior or authorize external actions.
