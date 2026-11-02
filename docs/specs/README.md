# Specification and scenario map

Accepted interview decisions now feed the [prototype contract](prototype.md) and
[production HLD](../architecture/production.md). Local implementation checks exist; real provider/source checks are recorded separately in verification.
Written scenarios are contracts, not automatic proof of complete coverage.

| Scope | Primary contract | Scenarios/checks | Current evidence |
| --- | --- | --- | --- |
| Core and deliverables | [Requirements](requirements.md) | CORE/DEL obligations | Manual source-to-obligation review |
| Eight requirements | [Requirements](requirements.md) | REQ-01 through REQ-08 | Prototype/design distinction checked against original text |
| Safety, metrics, RAG, recovery and deletion | [Corner-case inventory](requirements.md#corner-cases-to-settle-and-test) | Cases in the inventory | See prototype acceptance checks and verification limits |
| Agent, SQL and retrieval separation | [Architecture analysis](../architecture/overview.md) | Comparison with actual Resourcing paths | Targeted static inspection and source SQLite read-only checks |
| Full prototype | [Prototype contract](prototype.md) | Runtime/data/SQL/agent/report/budget acceptance table | Local checks and bounded live/source review; see verification |
| All production requirements | [Production HLD](../architecture/production.md) | Service/data/identity/learning/persona/QA/operations design | Design review only; not deployed |
| Imported development harness | [Verification](../development/verification.md) | Existing tooling unit/link/progress checks | Actual results recorded in progress.json |

Use the [workflow](../development/workflow.md) for impact review and unresolved policy
choices. Do not copy staffing benchmark answers into retail prompts. The application
[evaluation runner](../../src/retail_assistant/evaluation.py) separates local mechanics
from live outputs requiring review; the repository harness itself does not evaluate
report quality or SQL semantics.
