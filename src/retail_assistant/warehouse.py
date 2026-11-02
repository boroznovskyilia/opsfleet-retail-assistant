"""Real BigQuery reads: trusted source projection, bounded jobs, no DataFrame allocation."""

import hashlib
import time
from datetime import date, timedelta
from decimal import Decimal

from google.api_core import exceptions as google_errors
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery

from .config import AppError, USERS, timeout_for
from .telemetry import event
from .warehouse_sql import product_catalog

EXPECTED = {
    "orders": {"order_id", "user_id", "status"},
    "order_items": {
        "id",
        "order_id",
        "user_id",
        "product_id",
        "status",
        "created_at",
        "returned_at",
        "sale_price",
    },
    "products": {"id", "name", "category", "brand", "department"},
    "users": {"id", "state", "country"},
}
JOB_BYTES = 256 * 1024 * 1024
TURN_BYTES = 1024 * 1024 * 1024


def scalar(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class BigQueryWarehouse:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.location = None
        self.checked = False

    def close(self):
        if self.client is not None:
            self.client.close()

    def doctor(self, remaining=None):
        def timeout():
            return timeout_for(remaining, 8)

        if not self.settings.project:
            raise AppError(
                "bigquery_configuration",
                "Set GOOGLE_CLOUD_PROJECT and configure local Google ADC; see setup instructions.",
            )
        try:
            if self.client is None:
                self.client = bigquery.Client(project=self.settings.project)
            if not self.checked:
                dataset = self.client.get_dataset(
                    "bigquery-public-data.thelook_ecommerce",
                    retry=None,
                    timeout=timeout(),
                )
                self.location = dataset.location
                for name, required in EXPECTED.items():
                    table = self.client.get_table(
                        "bigquery-public-data.thelook_ecommerce." + name,
                        retry=None,
                        timeout=timeout(),
                    )
                    if not required <= {f.name for f in table.schema}:
                        raise AppError(
                            "schema_drift",
                            "Source schema differs from the documented contract; analysis was not executed.",
                        )
                self.checked = True
        except GoogleAuthError:
            raise AppError(
                "bigquery_auth",
                "Google ADC is missing or expired; run gcloud auth application-default login locally.",
            ) from None
        except google_errors.GoogleAPICallError:
            raise AppError(
                "bigquery_metadata",
                "Cannot read source metadata; check Google credentials, project access and availability.",
            ) from None
        return {
            "schema": "compatible required fields",
            "location": self.location,
            "data_read": False,
        }

    def query(self, query, owner, period, secret, remaining, trace, scan_used=0):
        self.doctor(remaining)
        end = (date.fromisoformat(period["end"]) + timedelta(days=1)).isoformat()
        parameters = [
            bigquery.ScalarQueryParameter("product_parity", "INT64", USERS[owner]),
            bigquery.ScalarQueryParameter("alias_secret", "STRING", secret),
            bigquery.ScalarQueryParameter("period_start", "STRING", period["start"]),
            bigquery.ScalarQueryParameter("period_end", "STRING", end),
            *[bigquery.ScalarQueryParameter(*p) for p in query.parameters],
        ]
        start = time.monotonic()
        job = None
        fingerprint = hashlib.sha256(query.sql.encode()).hexdigest()
        try:
            timeout = min(10, remaining())
            if timeout <= 0:
                raise AppError(
                    "turn_budget", "Turn deadline reached before query execution."
                )
            dry = self.client.query(
                query.sql,
                location=self.location,
                job_config=bigquery.QueryJobConfig(
                    dry_run=True, use_query_cache=False, query_parameters=parameters
                ),
                retry=None,
                job_retry=None,
                timeout=timeout,
            )
            estimated = dry.total_bytes_processed
            if (
                estimated is None
                or estimated > JOB_BYTES
                or scan_used + JOB_BYTES > TURN_BYTES
            ):
                raise AppError(
                    "scan_budget",
                    "Query exceeds the job/turn scan budget; no data query was executed.",
                )
            left = remaining()
            if left <= 0:
                raise AppError(
                    "turn_budget", "Turn deadline reached after query validation."
                )
            config = bigquery.QueryJobConfig(
                query_parameters=parameters,
                maximum_bytes_billed=JOB_BYTES,
                job_timeout_ms=max(1, int(min(15, left) * 1000)),
            )
            job = self.client.query(
                query.sql,
                location=self.location,
                job_config=config,
                retry=None,
                job_retry=None,
                timeout=min(8, left),
            )
            if remaining() <= 0:
                raise AppError(
                    "turn_budget", "Turn deadline reached before fetching results."
                )
            iterator = job.result(
                timeout=min(15, remaining()),
                retry=None,
                job_retry=None,
                max_results=101,
                page_size=101,
            )
            rows = [{k: scalar(v) for k, v in row.items()} for row in iterator]
            if sum(len(str(r).encode()) for r in rows) > 64 * 1024:
                raise AppError(
                    "result_budget",
                    "Query result exceeds the bounded payload; narrow the grouping.",
                )
            result = {
                "query_id": trace["query_id"],
                "sql": query.logical,
                "executed_sql": query.sql,
                "rows": rows[:100],
                "truncated": len(rows) > 100,
                "requested_limit": query.limit,
                "ranking_exception": query.ranking,
                "period": period,
                "scope": "even product IDs" if USERS[owner] == 0 else "odd product IDs",
                "scan_reservation": JOB_BYTES,
                "scan_bytes": job.total_bytes_processed,
                "job_id": job.job_id,
            }
            event(
                "query_completed",
                **trace,
                sql_sha256=fingerprint,
                rows=len(result["rows"]),
                truncated=result["truncated"],
                bytes=job.total_bytes_processed,
                job_id=job.job_id,
                latency_ms=round((time.monotonic() - start) * 1000),
            )
            return result
        except AppError:
            raise
        except google_errors.BadRequest:
            raise AppError(
                "invalid_sql",
                "BigQuery rejected query syntax/schema; one correction may preserve the original filters.",
            ) from None
        except (TimeoutError, google_errors.DeadlineExceeded):
            raise AppError(
                "query_timeout",
                "BigQuery timed out; any verified earlier results remain available.",
            ) from None
        except google_errors.GoogleAPICallError:
            raise AppError(
                "bigquery_unavailable",
                "BigQuery is unavailable or access is denied; no weaker execution path was used.",
            ) from None
        finally:
            if job is not None and job.state != "DONE":
                try:
                    job.cancel(retry=None, timeout=2)
                except (
                    google_errors.GoogleAPICallError,
                    GoogleAuthError,
                    TimeoutError,
                ):
                    event("query_cancel_failed", **trace, sql_sha256=fingerprint)

    def catalog(self, owner, remaining):
        self.doctor(remaining)
        sql, parameters = product_catalog()
        config = bigquery.QueryJobConfig(
            maximum_bytes_billed=JOB_BYTES,
            job_timeout_ms=max(1, int(timeout_for(remaining, 8) * 1000)),
            query_parameters=[
                bigquery.ScalarQueryParameter("parity", "INT64", USERS[owner]),
                *[bigquery.ScalarQueryParameter(*p) for p in parameters],
            ],
        )
        job = None
        try:
            job = self.client.query(
                sql,
                job_config=config,
                location=self.location,
                retry=None,
                job_retry=None,
                timeout=timeout_for(remaining, 8),
            )
            return {
                "rows": [
                    dict(r)
                    for r in job.result(
                        timeout=timeout_for(remaining, 8),
                        retry=None,
                        job_retry=None,
                        max_results=50,
                    )
                ],
                "subset": True,
                "note": "First 50 permitted products; this is a catalogue sample, not sales or the full product set.",
            }
        except (google_errors.GoogleAPICallError, TimeoutError):
            raise AppError(
                "catalog_unavailable", "Permitted product catalogue is unavailable."
            ) from None
        finally:
            if job is not None and job.state != "DONE":
                try:
                    job.cancel(retry=None, timeout=2)
                except (
                    google_errors.GoogleAPICallError,
                    GoogleAuthError,
                    TimeoutError,
                ):
                    event("catalog_cancel_failed", user=owner)
