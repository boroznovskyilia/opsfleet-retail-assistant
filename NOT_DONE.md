# Remaining work and deliberate limits

## Remaining production/quality validation

- Local Google ADC/Sandbox and the OpenRouter key are configured; metadata and bounded
  real BigQuery/model checks are recorded in the verification guide. Source freshness,
  currency convention and historical as-of semantics still need business confirmation.
- Live cases and source-number checks are a limited AI-assisted acceptance review,
  not an independent human analyst study, held-out benchmark or reliability estimate.
  Executive UX, realistic production load and repeated-run quality remain unmeasured.
- Provisioning the production HLD, production authentication/entitlements, reviewed
  learning/persona tools, monitoring/retention/HA and direct submission messages remain outside
  this take-home prototype's accepted runtime scope.

## Prototype boundaries

- Demo user selection is not production login. Product parity is a visible sample
  entitlement model; a local machine owner can edit the code/state.
- Flat sales SELECTs only; no arbitrary SQL joins/CTEs/windows or custom metrics.
  Required source joins are trusted code. Churn/causal proof/FX are not predefined.
- Five-customer suppression is not anonymity; individual ranking intentionally has
  the owner-approved pseudonym+amount exception. Input/output redaction is basic and
  cannot detect every personal name/free-text identifier. Database PII columns are
  excluded independently of that scanner.
- Four Golden examples are educational, not supplied human analyst reports or gold
  answer oracles. Complete tiny-catalogue selection is not a scalable vector index.
- No production auth, deployment, preference learning, system self-improvement,
  non-developer persona UI, charts/email/web tools or external alerting is implemented.
- No mid-turn graph checkpoint resume, automatic retention, multi-worker conversation
  orchestration or production load testing. Narrow storage/budget races are tested
  across independent processes. Owned history/actions/receipts/spend survive restart. Unknown
  provider costs remain reserved, which can exhaust the local budget conservatively.
- The turn deadline is best effort at remote cancellation boundaries. The native
  BigQuery SDK runs in a worker thread; cancelling its await does not immediately stop
  an in-flight SDK call, which remains bounded by its own timeouts. The
  recorded timings cover only the tested cases. Tests do not prove unseen-question quality.

Production application deployment and direct messages to the hiring team were not
performed. Repository publication is tracked in [progress](docs/plans/progress.json).
A development Google Sandbox project/ADC was configured.
