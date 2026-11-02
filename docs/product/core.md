# Product core

The supplied assignment describes a retail analytics chat assistant for non-technical
executives. The initial analysis and harness setup are followed by the owner's
requested vision interview, detailed specification and application implementation,
in that order. Live task state and unanswered interview questions belong in
progress.json; accepted product choices are recorded below.

## Owner-selected direction

On 2026-11-02 the owner selected a strong take-home submission within the original
scope, a flagship sales/spending comparison with factor analysis, and clarification
of material ambiguity while explicitly disclosing safe assumptions. These choices
do not select a framework or settle the full privacy policy.

The second interview round selected spending per active buyer, decomposed into order
frequency and average order value. Sales use the sum of item sale prices for completed
orders, excluding cancellations and returns. The data contract must map this business
rule to verified source statuses/date fields and consistent order/item/customer grains;
no live BigQuery schema check has been run yet. An active buyer has at least one
qualifying completed order during the selected period involving permitted products.
The buyer denominator, order count and amounts use the same permitted sales cohort;
do not derive activity or full-order value from forbidden products. Detailed mixed-
product order and timestamp handling belongs in the data contract.

For time-dependent analysis, an unspecified period must be clarified before queries,
rather than silently defaulting to a month or 90-day window. Reuse of an explicitly
established conversational period and non-temporal schema/catalogue questions need
clear handling in the specification, without inventing an analytical time window.

The CLI prototype uses two predefined demo identities with different product grants.
Authorization checks are real and grants are code/configuration-owned; demo identity
selection is not production authentication. The production HLD must describe trusted
identity and permission enforcement separately. Reasons and accepted choices are in
the [decision register](../decisions/README.md). The owner selected LangGraph and
English as the primary CLI/report/demo language. Exact personal framework experience
was not supplied and must not be fabricated for the submission.

The privacy direction allows aggregates and pseudonymous customer references, with
direct PII excluded before model input as well as from final output. Metrics for
groups below five customers are suppressed with a suggestion to broaden the query;
this educational rule does not establish anonymity. The owner explicitly permits an
exception for individual customer rankings: pseudonymous ID and amount only, without
personal attributes. Other grouped customer analyses retain the threshold. Do not
present the exception as anonymous aggregate reporting.

Explanations distinguish measured factors from hypotheses. Recommendations identify
how to test a hypothesis rather than implying that observational sales differences
prove a causal mechanism.

Reports are saved only on an explicit create/save request; ordinary analytical replies
remain conversation history. Confirmed deletion removes a report from the saved-report
library while preserving the conversation, including previously delivered content.
The CLI must explain that boundary before deletion; it must not promise that deleting
a library item erases all copies or the history. Confirmation uses an explicit
`/confirm <action_id>` command; rejection uses `/reject`. Decisions refer to stored
previewed terms, not a fresh model-generated selection. Report mention searches
match the supplied phrase in owned titles/bodies without case sensitivity, covering
the full owned library. Do not infer aliases such as CX = Client X. Show the search
condition and selected reports before confirmation.

The prototype also includes a small clearly educational Golden corpus of 3-5 linked
question/SQL/report examples with working retrieval. These are labeled sample methods,
not supplied expert knowledge, current sales truth or evaluation oracles. User
preferences, the system learning loop and no-redeploy persona management remain
production-design topics rather than additional prototype implementations.

The analytical agent may autonomously choose further read-only queries inside
code-enforced budgets, showing concise progress and clarifying material ambiguity.
The owner selected a target of up to one minute for complex analysis, not a measured
service guarantee. If the budget is exhausted, return verified partial evidence,
identify missing work and offer continuation rather than guessing or looping.
Numeric call/token/scan/cost limits remain engineering work for the specification.
Paid OpenRouter development/evaluation calls have an owner-authorized cumulative
USD 5 ceiling. Stop at that cap; it does not reset for a new run/conversation. The
provider key, funding and BigQuery Sandbox/ADC setup are local prerequisites, not
credentials to be stored in chat or committed.

## User and outcome

An executive asks questions about sales, customers and products, follows up in the
same conversation and requests a report with findings and action items. Fresh database
results support numerical claims; approved historical analyst examples guide the
interpretation and method. The assistant also manages the user's saved reports.

## Domain language

| Term | Meaning |
| --- | --- |
| Application user | Executive using the assistant; distinct from a customer row in the users table |
| Product scope | Products that the application user is permitted to analyze |
| Golden trio | Historical expert question, SQL and analyst report; guidance rather than current numerical truth |
| Saved report | User-owned output that can be selected for explicitly confirmed deletion |
| Conversation | Follow-up context and the association used by delete-this-conversation requests |
| PII | Direct personal data excluded from model input and final answers; exact field policy still needs source mapping |
| Development harness | Repository instructions, durable work state and validators; no application runtime |

## Priorities and constraints

Design all eight assignment requirements. Implement four named cross-cutting
requirements in a future prototype: safety/PII/product authorization, deletion
confirmation, bounded recovery and observability. The working core also needs natural
language analysis, dynamically generated BigQuery SQL, follow-ups and reports with
action items. The specified interface is CLI; React is not required.

The dataset and four tables are specified; Gemini is preferred and a framework must
be used and explained. Cloud deployment, graphs, email and web tools are not required
for the prototype. The assignment expects 6-12 hours and emphasizes design/explanation.

Requirements, open questions and examples live in [requirements](../specs/requirements.md).
The [architecture analysis](../architecture/overview.md) records proposed approaches,
not an implemented or owner-approved cloud stack.
