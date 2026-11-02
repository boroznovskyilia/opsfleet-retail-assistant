# Recorded live acceptance review — 2026-11-02

The prototype was exercised against real Gemini 3.8 Flash through OpenRouter and
bigquery-public-data.thelook_ecommerce. [Machine-readable summary](live-results.json)
records exact source fingerprints, timings, check counts and budget. Full responses,
query/job references and retained failures remain in ignored `.runtime/evaluation`.
This is an AI-assisted source/intent review, not an independent human analyst study.

## Real cases and outcomes

| Case | Observed outcome | Time |
| --- | --- | --- |
| April state spending comparison | Two queries; separate global total; frequency/AOV factors distinguished from hypotheses; sample coverage disclosed | 20.78s |
| April monthly revenue | One query; explicitly states one month cannot establish a temporal trend | 18.43s |
| April requested product report | Four queries; explains individual product privacy suppression, uses clearly labeled category/department context, saves insights/actions | 57.84s |
| Two publishable permitted products, 2020-01-01 through 2026-10-31 | Compares IDs 24144 and 2058, each with eight buyers; explains equal frequency and differing AOV; saves report/actions | 19.50s |
| Real CLI under analyst_b | Pseudonymous ranking, inherited-period monthly follow-up, explicit save, preview, restart, confirm/repeat, retained history | 28.61s for both analytical turns and process workflow |

All four analytical cases ended without execution issues. The runner retains
review_required/exit 2 because successful execution alone is not correctness. Read
individual report limitations; unavailable product detail was not invented.

## Independent source-number checks

[Source oracle SQL](source-oracle.sql) independently aggregates the same completed,
non-returned, UTC/product-scoped cohort directly from the four raw tables. It does
not call the application's SQL compiler and does not expose raw customer PII.
Bounded reference jobs verified **239 numerical values**, including the two product
comparisons and analyst_b's separate monthly value. Counted joined facts equal
DISTINCT item IDs; the JOIN did not multiply amounts in these checked cohorts.
For April, zero individual product groups pass five buyers, which explains the empty
product result rather than implying zero global sales. Wider-period products pass.

The final repeated base oracle job used a cached result; the earlier independent
reference read processed 16,661,405 bytes. Extra product/odd-user checks disabled the
query cache and processed 14,971,573 bytes each. These are recorded source checks,
not an immutable future dataset snapshot or arbitrary-SQL semantic proof.

## Recorded example

This excerpt uses actual live values, rounded here for readability. The full-precision
query results and generated report are retained in the private run artifact.

```text
You> Create a report comparing permitted product IDs 24144 and 2058
     from 2020-01-01 through 2026-10-31. Compare revenue and spending
     per active buyer, explain frequency versus average order value,
     distinguish hypotheses and propose actions to validate.
```

| Product ID | Revenue, dataset units | Buyers | Orders | Spend per buyer | Order frequency |
| --- | --- | --- | --- | --- | --- |
| 24144 | 1045.20 | 8 | 8 | 130.65 | 1.00 |
| 2058 | 148.48 | 8 | 8 | 18.56 | 1.00 |

The report attributes the measured spending difference to AOV with equal buyer/order
counts. Higher unit pricing is labeled a hypothesis; checking item quantities/order
composition is a proposed validation, not a proven causal finding.

## Failures retained and corrected

- Initial OpenRouter requests failed HTTP 404 during routing. Removed an unsupported
  optional parallel-tool flag and used the model-advertised max_tokens parameter;
  HTTP status now appears in safe diagnostics. No alternate model was substituted.
- One early report used all model calls for investigation and returned partial tables.
  The last of six calls is now reserved for tool-free composition. Query/tool exhaustion
  preserves paired tool replies and permits a final grounded report.
- Real CLI review caught a phone scanner consuming an adjacent year and ISO date.
  A reproducing test and date-boundary fix preserve dates while still masking phones.
- Final deletion review caught newline ambiguity in concatenated title/body hashes.
  The existing frozen title is now checked explicitly, with a reproducing regression.
  No hash-format migration was needed. Final CLI command-only save/preview/restart/
  confirm/repeat against retained live history passed without more paid calls.

The last change touched only store.py and its regression. Byte comparison against the
clean copy used for the paid live run verified that analytical/transport code stayed
unchanged. The summary preserves both fingerprints; it does not relabel old results
as runs on the final revision. All 55 final local tests and final store process checks
were rerun. Earlier failed/partial artifacts were preserved.

## Cost and remaining limits

OpenRouter reported **USD 0.11035725** usage at the recorded check. The local ledger
holds USD 0.88775 including conservative reservations for failed/uncertain requests;
these are different measurements. The dedicated key has a non-resetting USD 5 cap.
The Google project has no linked billing account. No runtime ledger was reset.

Dates/scopes, numerical facts, sample limits, causal wording and proposed actions were
reviewed for these cases. No independent expert review, held-out accuracy, repeated-run
reliability, executive user study or production load/SLO claim follows. Prototype
limitations remain in [NOT_DONE](../../NOT_DONE.md) and the [conformance matrix](conformance.md).
