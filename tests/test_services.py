import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from retail_assistant.config import AppError
from retail_assistant.responses import parse_reply
from retail_assistant.services.analysis import AnalysisService
from retail_assistant.services.knowledge import GoldenKnowledge
from retail_assistant.services.reports import ReportService
from retail_assistant.store import Store
from retail_assistant.warehouse import TURN_BYTES
from support import answer


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = await self.enterAsyncContext(
            Store(Path(self.temp.name) / "app.sqlite")
        )
        self.thread = (await self.store.thread("analyst_a"))["id"]

    async def test_uncertain_queries_keep_scan_reservations_and_stop_at_four(self):
        warehouse = Mock()

        def fail(*args):
            self.assertEqual(self.store.engine.pool.checkedout(), 0)
            raise AppError("invalid_sql", "Rejected after dispatch")

        warehouse.query.side_effect = fail
        service = AnalysisService(
            "analyst_a",
            {"start": "2026-04-01", "end": "2026-04-30"},
            warehouse,
            self.store,
            lambda: 60,
            {},
        )
        service.get_schema()
        for _ in range(4):
            with self.assertRaises(AppError):
                await service.query("SELECT SUM(amount) AS revenue FROM sales")
        self.assertEqual(service.scan_used, TURN_BYTES)
        with self.assertRaises(AppError) as error:
            await service.query("SELECT SUM(amount) AS revenue FROM sales")
        self.assertEqual(error.exception.code, "query_budget")
        self.assertEqual(warehouse.query.call_count, 4)

    async def test_negated_deletion_cannot_create_preview_or_delete(self):
        await self.store.save("analyst_a", self.thread, "Client X", "Body")
        service = ReportService(self.store, "analyst_a", self.thread)
        for request in [
            "Don't delete reports mentioning Client X",
            "Never remove reports",
            "Do not delete reports",
        ]:
            with self.subTest(request=request), self.assertRaises(AppError) as error:
                await service.prepare("Client X", user_text=request)
            self.assertEqual(error.exception.code, "action_not_requested")
        self.assertIsNone(await self.store.pending("analyst_a", self.thread))
        self.assertEqual(len(await service.list()), 1)

    async def test_golden_empty_unknown_and_provenance(self):
        knowledge = GoldenKnowledge()
        self.assertFalse(knowledge.retrieve([])["match_found"])
        with self.assertRaises(AppError):
            knowledge.retrieve(["invented"])
        result = knowledge.retrieve(["spending-decomposition"])
        self.assertIn("Educational", result["provenance"])
        self.assertEqual(
            set(result["trios"][0]) & {"question", "sql", "report"},
            {"question", "sql", "report"},
        )

    async def test_model_cannot_claim_analysis_without_current_evidence(self):
        for reply in [answer(ids=["invented"]), answer(), {"content": "[]"}]:
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                parse_reply(reply["content"], [], False)
        complete = answer(ids=["q1"])
        self.assertEqual(
            parse_reply(complete["content"], [{"query_id": "q1"}], True)["kind"],
            "analysis",
        )

    async def test_cli_save_and_agent_save_share_owned_report_rules(self):
        (
            await self.store.append(
                "analyst_a", self.thread, "assistant", "Verified evidence"
            )
        )
        service = ReportService(self.store, "analyst_a", self.thread)
        await service.save_last("First report")
        await service.save_requested("Create a report", "Verified evidence", True)
        await service.save_requested("Explain the result", "Ordinary response", True)
        self.assertEqual(len(await service.list()), 2)
        other = ReportService(self.store, "analyst_b", self.thread)
        with self.assertRaises(AppError):
            await other.save_last("Foreign report")
