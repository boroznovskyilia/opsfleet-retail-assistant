"""Scoped analytical reads and their per-turn evidence/scan budget."""

import asyncio

from ..config import AppError
from ..policy import compile_query, schema
from ..warehouse import JOB_BYTES, TURN_BYTES


class AnalysisService:
    def __init__(self, owner, period, warehouse, store, remaining, trace):
        self.owner, self.period = owner, period
        self.warehouse, self.store = warehouse, store
        self.remaining, self.trace = remaining, trace
        self.schema_seen = False
        self.query_attempts = 0
        self.scan_used = 0
        self.results = []

    def get_schema(self):
        self.schema_seen = True
        return schema()

    @property
    def exhausted(self):
        return self.query_attempts >= 4 or self.scan_used >= TURN_BYTES

    async def products(self):
        self._check_scan()
        self.scan_used += JOB_BYTES
        return await asyncio.to_thread(
            self.warehouse.catalog, self.owner, self.remaining
        )

    async def query(self, sql):
        if self.period is None:
            raise AppError(
                "missing_period",
                "Ask the user for an explicit analysis period before sales queries.",
            )
        if not self.schema_seen:
            raise AppError("missing_schema", "Read get_schema before generating SQL.")
        if self.query_attempts >= 4:
            raise AppError("query_budget", "Four-query turn limit reached.")
        self.query_attempts += 1
        query = compile_query(sql)
        self._check_scan()
        previous_scan = self.scan_used
        # Reserve before dispatch; failed/uncertain reads must not refund scan capacity.
        self.scan_used += JOB_BYTES
        result = await asyncio.to_thread(
            self.warehouse.query,
            query,
            self.owner,
            self.period,
            await self.store.secret(self.owner),
            self.remaining,
            {**self.trace, "query_id": "q" + str(self.query_attempts)},
            previous_scan,
        )
        self.results.append(result)
        public = {
            k: v
            for k, v in result.items()
            if k not in {"executed_sql", "scan_reservation"}
        }
        return {
            **public,
            "rows": result["rows"][:8],
            "explanation_sample": len(result["rows"]) > 8,
            "empty_result": not result["rows"],
            "diagnostic": "Check the requested period, product identity and filters. A valid empty or privacy-suppressed cohort is not evidence of zero sales; never weaken access/privacy or silently change intent."
            if not result["rows"]
            else None,
        }

    def _check_scan(self):
        if self.remaining() <= 0:
            raise AppError(
                "turn_budget", "Turn deadline reached before analytical access."
            )
        if self.scan_used + JOB_BYTES > TURN_BYTES:
            raise AppError("scan_budget", "Turn scan reservation exhausted.")
