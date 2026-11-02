import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from retail_assistant.responses import FINAL_SCHEMA
from retail_assistant.tools import TOOLS
from retail_assistant.config import AppError, Settings
from retail_assistant.llm import OpenRouter
from retail_assistant.store import Store
from support import answer


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(
            runtime=Path(self.temp.name), api_key="test-secret-not-real"
        )
        self.store = await self.enterAsyncContext(
            Store(self.settings.runtime / "app.sqlite")
        )
        self.posts = []

    def client(self, mode="ok", limit=5, reset=None):
        def respond(request):
            if request.url.path.endswith("/key"):
                return httpx.Response(
                    200, json={"data": {"limit": limit, "limit_reset": reset}}
                )
            if request.url.path.endswith("/models"):
                return httpx.Response(
                    200,
                    json={
                        "data": [
                            {
                                "id": self.settings.model,
                                "supported_parameters": [
                                    "tools",
                                    "tool_choice",
                                    "response_format",
                                    "max_tokens",
                                    "reasoning",
                                ]
                                if mode != "unsupported"
                                else [],
                                "pricing": {
                                    "prompt": "0.00000075",
                                    "completion": "0.00000375",
                                },
                            }
                        ]
                    },
                )
            self.posts.append(json.loads(request.content))
            if mode == "retry" and len(self.posts) == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "0"},
                    json={"error": {"message": "DO_NOT_EXPOSE_RAW_ERROR"}},
                )
            if mode == "failure":
                return httpx.Response(
                    401, json={"error": {"message": "DO_NOT_EXPOSE_RAW_ERROR"}}
                )
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": answer(kind="clarification")}],
                    "usage": {}
                    if mode == "unknown"
                    else {"cost": 0.001, "prompt_tokens": 10, "completion_tokens": 10},
                },
            )

        client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=httpx.MockTransport(respond),
        )
        self.addAsyncCleanup(client.aclose)
        return client

    async def call(self, client):
        return await OpenRouter(self.settings, self.store, client).call(
            [{"role": "user", "content": "test"}],
            TOOLS,
            lambda: 60,
            {"request": "test"},
            FINAL_SCHEMA,
        )

    async def test_caps_structured_tool_contract_and_actual_cost(self):
        reply = await self.call(self.client())
        self.assertEqual(reply["role"], "assistant")
        self.assertEqual((await self.store.spent())["usd"], 0.001)
        self.assertTrue(self.posts[0]["provider"]["require_parameters"])
        self.assertEqual(self.posts[0]["response_format"], FINAL_SCHEMA)
        self.assertEqual(self.posts[0]["max_tokens"], 1500)
        self.assertNotIn("parallel_tool_calls", self.posts[0])

    async def test_final_composition_omits_tool_parameters(self):
        (
            await OpenRouter(self.settings, self.store, self.client()).call(
                [], [], lambda: 60, {}, FINAL_SCHEMA
            )
        )
        self.assertNotIn("tools", self.posts[0])
        self.assertNotIn("tool_choice", self.posts[0])
        self.assertEqual(self.posts[0]["response_format"], FINAL_SCHEMA)

    async def test_provider_key_limit_required_before_paid_dispatch(self):
        for limit, reset in [(None, None), (10, None), (5, "monthly")]:
            with self.subTest(limit=limit, reset=reset), self.assertRaises(AppError):
                await self.call(self.client(limit=limit, reset=reset))
        self.assertEqual(self.posts, [])
        self.assertEqual((await self.store.spent())["usd"], 0)

    async def test_unsupported_model_parameters_fail_before_generation(self):
        with self.assertRaises(AppError) as error:
            await self.call(self.client("unsupported"))
        self.assertEqual(error.exception.code, "model_capability")
        self.assertEqual(self.posts, [])
        self.assertEqual((await self.store.spent())["usd"], 0)

    async def test_unknown_cost_keeps_reservation(self):
        with self.assertRaises(AppError) as error:
            await self.call(self.client("unknown"))
        self.assertEqual(error.exception.code, "unknown_cost")
        self.assertGreater((await self.store.spent())["usd"], 0.001)

    async def test_retry_reserves_each_physical_attempt(self):
        await self.call(self.client("retry"))
        self.assertEqual(len(self.posts), 2)
        self.assertGreater((await self.store.spent())["usd"], 0.001)

    async def test_error_redacted_and_not_retried(self):
        with self.assertRaises(AppError) as error:
            await self.call(self.client("failure"))
        self.assertNotIn("DO_NOT_EXPOSE", str(error.exception))
        self.assertIn("HTTP 401", str(error.exception))
        self.assertEqual(len(self.posts), 1)

    async def test_expired_turn_cannot_start_even_metadata_or_reserve_cost(self):
        def forbidden(request):
            self.fail("An expired turn sent an HTTP request")

        client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=httpx.MockTransport(forbidden),
        )
        self.addAsyncCleanup(client.aclose)
        with self.assertRaises(AppError) as error:
            (
                await OpenRouter(self.settings, self.store, client).call(
                    [], TOOLS, lambda: 0, {}, FINAL_SCHEMA
                )
            )
        self.assertEqual(error.exception.code, "turn_budget")
        self.assertEqual((await self.store.spent())["usd"], 0)

    async def test_cancellation_keeps_reservation_and_no_session_during_http(self):
        dispatched = asyncio.Event()

        async def respond(request):
            self.assertEqual(self.store.engine.pool.checkedout(), 0)
            dispatched.set()
            await asyncio.Event().wait()

        client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=httpx.MockTransport(respond),
        )
        self.addAsyncCleanup(client.aclose)
        model = OpenRouter(self.settings, self.store, client)
        model.checked = True
        task = asyncio.create_task(model.call([], TOOLS, lambda: 60, {}, FINAL_SCHEMA))
        await asyncio.wait_for(dispatched.wait(), 3)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertGreater((await self.store.spent())["usd"], 0)
        self.assertEqual(self.store.engine.pool.checkedout(), 0)

    async def test_expired_after_reserving_cannot_dispatch(self):
        from unittest.mock import AsyncMock, patch

        client = self.client()
        model = OpenRouter(self.settings, self.store, client)
        model.checked = True
        remaining = [60]
        reserve = self.store.reserve

        async def expire(*args):
            result = await reserve(*args)
            remaining[0] = 0
            return result

        with patch.object(self.store, "reserve", new=AsyncMock(side_effect=expire)):
            with self.assertRaises(AppError) as error:
                await model.call([], TOOLS, lambda: remaining[0], {}, FINAL_SCHEMA)
        self.assertEqual(error.exception.code, "turn_budget")
        self.assertEqual(self.posts, [])
