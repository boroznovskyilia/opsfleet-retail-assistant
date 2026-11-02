# Integration prerequisites

Checked against official provider documentation on 2026-11-02. The prototype supports local credentials and separately recorded live checks.

## Local configuration

From the repository root, create the ignored local file only if it does not exist:

```sh
test -e .env || cp .env.example .env
```

Edit `.env` locally. Do not send keys or credential files through chat.

## Gemini through OpenRouter

Create a named API key in [OpenRouter settings](https://openrouter.ai/settings/keys),
set a non-resetting USD 5 credit limit, and put it in OPENROUTER_API_KEY. The agreed
development/evaluation ceiling is cumulative, not USD 5 per run; leave
OPENROUTER_BUDGET_USD at 5. The app reserves cost before each physical model attempt.
Model calls consume OpenRouter credits. [Authentication and credit limits](https://openrouter.ai/docs/api_reference/authentication).

The configured pinned model is `google/gemini-3.8-flash`, currently listed with tool
calling and structured outputs. [Provider capabilities](https://openrouter.ai/google/gemini-3.8-flash/providers).
Listing is not a successful integration test or an analytical quality benchmark.

## BigQuery Sandbox

Open [BigQuery Studio](https://console.cloud.google.com/bigquery), sign in and create
a project using the [Sandbox instructions](https://docs.cloud.google.com/bigquery/docs/sandbox).
No card/billing account is required for Sandbox; the documented query allowance is
1 TiB processed per month. Verify the new project has no linked billing account;
existing Google accounts may create a project with a billing association. Use the
project-specific Billing page, not an account-wide cost summary.
[Verify billing status](https://docs.cloud.google.com/billing/docs/how-to/verify-billing-enabled).

Put that project's ID in GOOGLE_CLOUD_PROJECT. The source tables remain in
`bigquery-public-data.thelook_ecommerce`; your project is where queries run.

## Local Google authentication

Install the Google Cloud CLI using the link in the
[official authentication guide](https://docs.cloud.google.com/bigquery/docs/authentication).
Then run locally:

```sh
gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

This explicit scope list excludes the unnecessary Cloud SQL login permission. Google
Cloud access still covers resources permitted to your Google account; review the
consent screen. For a browser on another surface, add --no-launch-browser and handle
the one-time code privately in the same local CLI session.

Replace YOUR_PROJECT_ID with the same Sandbox project. The second command associates
ADC quota with that project and requires serviceusage.services.use permission.
[Command reference](https://docs.cloud.google.com/sdk/gcloud/reference/auth/application-default/set-quota-project).

BigQuery uses ADC rather than an API key. [Authentication](https://docs.cloud.google.com/bigquery/docs/authentication/getting-started).
Keep generated credentials in their standard local location; no service-account JSON
key is needed for this local user flow. Authentication is not runtime product access.

## Verification boundary

Use `make doctor`, then a bounded read with dry-run estimation and a server-enforced
maximum_bytes_billed limit. The numeric budget is 256 MiB per analytical job and
1 GiB per turn. [Client configuration](https://github.com/googleapis/python-bigquery/blob/main/google/cloud/bigquery/job/query.py).
Doctor verifies metadata, not model generation or analytical correctness. See
[verification](verification.md) for measured local/live results and current limits.
Keep .env and ADC out of Git; no Google credentials need to be copied into .env.
