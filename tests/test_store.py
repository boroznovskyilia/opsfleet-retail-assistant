import asyncio
import json
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from sqlalchemy import event, select, update

from retail_assistant.config import AppError
from retail_assistant.models import Report, Spend
from retail_assistant.store import Store, digest, now


class StoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = await self.enterAsyncContext(
            Store(Path(self.temp.name) / "app.sqlite")
        )
        self.thread = (await self.store.thread("analyst_a"))["id"]
        self.other = (await self.store.thread("analyst_b"))["id"]

    async def seed(self, title="Client X"):
        return await self.store.save(
            "analyst_a", self.thread, title, "Completed sales report for Client X."
        )

    async def test_owned_preview_exact_set_restart_and_repeated_decision(self):
        await self.seed()
        await self.store.save(
            "analyst_b", self.other, "Client X", "Foreign owner report"
        )
        preview = await self.store.prepare("analyst_a", self.thread, "client x")
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)
        late = await self.seed("Later Client X")
        recovered = await self.enterAsyncContext(Store(self.store.path))
        receipt = await recovered.decide(
            "analyst_a", self.thread, preview["id"], "confirm"
        )
        self.assertEqual(receipt["deleted"], 1)
        self.assertEqual(
            [r["id"] for r in await recovered.reports("analyst_a")], [late]
        )
        self.assertEqual(
            await recovered.decide("analyst_a", self.thread, preview["id"], "confirm"),
            receipt,
        )
        self.assertEqual(len(await recovered.reports("analyst_b")), 1)
        with self.assertRaises(AppError):
            await recovered.decide("analyst_a", self.thread, preview["id"], "reject")

    async def test_reject_owner_thread_and_history(self):
        await self.seed()
        await self.store.append(
            "analyst_a", self.thread, "assistant", "Historic Client X report"
        )
        preview = await self.store.prepare("analyst_a", self.thread, conversation=True)
        with self.assertRaises(AppError):
            await self.store.decide("analyst_b", self.other, preview["id"], "confirm")
        await self.store.decide("analyst_a", self.thread, preview["id"], "reject")
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)
        preview = await self.store.prepare("analyst_a", self.thread, conversation=True)
        await self.store.decide("analyst_a", self.thread, preview["id"], "confirm")
        self.assertIn(
            "Historic", (await self.store.history("analyst_a", self.thread))[0]["body"]
        )

    async def test_stale_and_superseded(self):
        report = await self.seed()
        old = await self.store.prepare("analyst_a", self.thread, "Client X")
        new = await self.store.prepare("analyst_a", self.thread, "Client X")
        with self.assertRaises(AppError):
            await self.store.decide("analyst_a", self.thread, old["id"], "confirm")
        async with self.store.session(write=True) as session:
            await session.execute(
                update(Report).where(Report.id == report).values(body="changed")
            )
        with self.assertRaises(AppError):
            await self.store.decide("analyst_a", self.thread, new["id"], "confirm")
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)

    async def test_concurrent_confirm_is_idempotent_across_engines(self):
        await self.seed()
        preview = await self.store.prepare("analyst_a", self.thread, "Client X")
        other = await self.enterAsyncContext(Store(self.store.path))
        receipts = await asyncio.gather(
            *[
                store.decide("analyst_a", self.thread, preview["id"], "confirm")
                for store in (self.store, other)
            ]
        )
        self.assertEqual(receipts[0], receipts[1])
        self.assertEqual(await self.store.reports("analyst_a"), [])

    async def test_matching_is_literal_unicode_and_empty_safe(self):
        await self.seed("CLIENT X")
        self.assertIsNone(
            (await self.store.prepare("analyst_a", self.thread, "CX"))["id"]
        )
        with self.assertRaises(AppError):
            await self.store.prepare("analyst_a", self.thread, "")
        self.assertEqual(
            len(
                (await self.store.prepare("analyst_a", self.thread, "client x"))[
                    "reports"
                ]
            ),
            1,
        )
        await self.store.save("analyst_a", self.thread, "Straße", "Unicode body")
        self.assertEqual(
            len(
                (await self.store.prepare("analyst_a", self.thread, "STRASSE"))[
                    "reports"
                ]
            ),
            1,
        )

    async def test_budget_survives_restart_unknown_cost_and_reservation_concurrency(
        self,
    ):
        first = await self.store.reserve(Decimal("3"), Decimal("5"))
        recovered = await self.enterAsyncContext(Store(self.store.path))
        with self.assertRaises(AppError):
            await recovered.reserve(Decimal("3"), Decimal("5"))
        await recovered.settle(first, Decimal("1"))

        async def attempt(store):
            try:
                return await store.reserve(Decimal("3"), Decimal("5"))
            except AppError as error:
                self.assertEqual(error.code, "model_budget")
                return None

        results = await asyncio.gather(attempt(self.store), attempt(recovered))
        self.assertEqual(sum(x is not None for x in results), 1)
        self.assertEqual((await recovered.spent())["usd"], 4)
        with self.assertRaises(AppError):
            await recovered.reserve(Decimal("2"), Decimal("5"))

    async def test_preview_detects_changed_title(self):
        report = await self.seed()
        preview = await self.store.prepare("analyst_a", self.thread, "Client X")
        async with self.store.session(write=True) as session:
            await session.execute(
                update(Report)
                .where(Report.id == report)
                .values(title="Different client")
            )
        with self.assertRaises(AppError):
            await self.store.decide("analyst_a", self.thread, preview["id"], "confirm")
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)

    async def test_preview_rejects_title_body_boundary_change_even_when_digest_is_same(
        self,
    ):
        report = await self.store.save("analyst_a", self.thread, "Client X", "one\ntwo")
        preview = await self.store.prepare("analyst_a", self.thread, phrase="Client X")
        async with self.store.session(write=True) as session:
            await session.execute(
                update(Report)
                .where(Report.id == report)
                .values(title="Client X\none", body="two")
            )
        with self.assertRaises(AppError) as error:
            await self.store.decide("analyst_a", self.thread, preview["id"], "confirm")
        self.assertEqual(error.exception.code, "stale_selection")
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)

    async def test_legacy_database_preserves_period_history_alias_pending_and_spend(
        self,
    ):
        fixture = Path(__file__).parent / "fixtures/legacy-state.sqlite"
        expected = json.loads(fixture.with_suffix(".json").read_text())
        path = Path(self.temp.name) / "legacy.sqlite"
        shutil.copy2(fixture, path)
        recovered = await self.enterAsyncContext(Store(path))
        thread = expected["thread"]
        self.assertEqual(await recovered.secret("analyst_a"), expected["alias_digest"])
        self.assertEqual(
            await recovered.period("analyst_a", thread),
            {"start": "2026-04-01", "end": "2026-04-30"},
        )
        self.assertEqual(
            (await recovered.history("analyst_a", thread))[0]["body"],
            "Legacy verified report body",
        )
        self.assertEqual((await recovered.spent())["usd"], 0.35)
        self.assertEqual(
            (await recovered.pending("analyst_a", thread))["id"], expected["action"]
        )
        receipt = await recovered.decide(
            "analyst_a", thread, expected["action"], "confirm"
        )
        self.assertEqual(receipt["deleted"], 1)
        self.assertEqual(
            await recovered.decide("analyst_a", thread, expected["action"], "confirm"),
            receipt,
        )
        await recovered.settle(expected["reserved"], ".05")
        self.assertEqual((await recovered.spent())["usd"], 0.15)
        self.assertEqual(len(await recovered.history("analyst_a", thread)), 1)

    async def test_delete_and_receipt_rollback_together_on_failure(self):
        await self.seed()
        preview = await self.store.prepare("analyst_a", self.thread, "Client X")

        def fail_receipt(connection, cursor, statement, parameters, context, many):
            if statement.startswith("UPDATE actions"):
                raise RuntimeError("injected receipt failure")

        event.listen(
            self.store.engine.sync_engine, "before_cursor_execute", fail_receipt
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "injected receipt failure"):
                await self.store.decide(
                    "analyst_a", self.thread, preview["id"], "confirm"
                )
        finally:
            event.remove(
                self.store.engine.sync_engine, "before_cursor_execute", fail_receipt
            )
        self.assertEqual(len(await self.store.reports("analyst_a")), 1)
        self.assertEqual(
            (await self.store.pending("analyst_a", self.thread))["id"], preview["id"]
        )
        self.assertEqual(self.store.engine.pool.checkedout(), 0)

    async def test_cancellation_rolls_back_and_returns_connection(self):
        inserted = asyncio.Event()

        async def interrupted():
            async with self.store.session(write=True) as session:
                session.add(
                    Report(
                        id="cancelled",
                        owner="analyst_a",
                        thread=self.thread,
                        title="Cancel",
                        body="Body",
                        hash=digest("Cancel\nBody"),
                        created=now(),
                    )
                )
                await session.flush()
                inserted.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(interrupted())
        await asyncio.wait_for(inserted.wait(), 3)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(await self.store.reports("analyst_a"), [])
        self.assertEqual(self.store.engine.pool.checkedout(), 0)
        await self.seed()

    async def test_concurrent_tasks_have_separate_sessions(self):
        ready = asyncio.Event()
        identities = set()

        async def read():
            async with self.store.session() as session:
                identities.add(id(session))
                await session.scalar(select(Spend.id))
                if len(identities) == 2:
                    ready.set()
                await asyncio.wait_for(ready.wait(), 3)

        await asyncio.gather(read(), read())
        self.assertEqual(len(identities), 2)
        self.assertEqual(self.store.engine.pool.checkedout(), 0)

    async def test_store_context_disposes_engine_and_closes_idle_connections(self):
        store = Store(Path(self.temp.name) / "lifecycle.sqlite")
        closed, disposed = [], []
        event.listen(
            store.engine.sync_engine, "close", lambda *args: closed.append(True)
        )
        event.listen(
            store.engine.sync_engine,
            "engine_disposed",
            lambda *args: disposed.append(True),
        )
        async with store:
            await store.thread("analyst_a")
            self.assertEqual(store.engine.pool.checkedout(), 0)
        self.assertEqual(disposed, [True])
        self.assertTrue(closed)

    async def test_constraint_failure_redacts_parameters_and_session_recovers(self):
        with self.assertRaises(AppError) as error:
            async with self.store.session(write=True) as session:
                session.add(
                    Spend(
                        id="DO_NOT_EXPOSE", micros=-1, status="reserved", created=now()
                    )
                )
        self.assertEqual(error.exception.code, "storage_unavailable")
        self.assertNotIn("DO_NOT_EXPOSE", str(error.exception))
        self.assertEqual((await self.store.spent())["usd"], 0)
        self.assertEqual(self.store.engine.pool.checkedout(), 0)

    async def test_overrun_is_committed_before_error(self):
        key = await self.store.reserve(".1", "5")
        with self.assertRaises(AppError) as error:
            await self.store.settle(key, ".2")
        self.assertEqual(error.exception.code, "price_overrun")
        self.assertEqual(await self.store.spent(), {"usd": 0.2, "overruns": 1})

    async def test_budget_lock_is_shared_between_real_processes(self):
        worker = """import asyncio, sys
from pathlib import Path
from retail_assistant.store import Store
from retail_assistant.config import AppError
async def run():
    async with Store(Path(sys.argv[1])) as store:
        try:
            await store.reserve('3', '5')
            print('reserved')
        except AppError as error:
            print(error.code)
asyncio.run(run())
"""

        async def attempt():
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                worker,
                str(self.store.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), 15)
            self.assertEqual(process.returncode, 0, stderr.decode())
            return stdout.decode().strip()

        self.assertCountEqual(
            await asyncio.gather(attempt(), attempt()), ["reserved", "model_budget"]
        )
        self.assertEqual((await self.store.spent())["usd"], 3)
