import asyncio
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from retail_assistant.config import Settings
from retail_assistant.privacy import scrub
from retail_assistant.store import Store


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupt_at_prompt_exits_without_waiting_for_a_stdin_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "retail_assistant",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **os.environ,
                    "RUNTIME_DIR": temp,
                    "OPENROUTER_API_KEY": "",
                    "GOOGLE_CLOUD_PROJECT": "",
                },
            )
            try:
                await asyncio.wait_for(process.stdout.readuntil(b"You> "), 5)
                process.send_signal(signal.SIGINT)
                stdout, stderr = await asyncio.wait_for(process.communicate(), 3)
                self.assertEqual(process.returncode, 0, stderr.decode())
                self.assertIn(b"Conversation preserved", stdout)
                self.assertNotIn(b"Traceback", stderr)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    async def test_actual_cli_restart_and_confirmation_without_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            async with Store(Path(temp) / "app.sqlite") as store:
                thread = (await store.thread("analyst_a"))["id"]
                (
                    await store.save(
                        "analyst_a", thread, "Client X", "Retained history content"
                    )
                )
                (
                    await store.append(
                        "analyst_a", thread, "assistant", "Retained history content"
                    )
                )
                env = {
                    **os.environ,
                    "RUNTIME_DIR": temp,
                    "OPENROUTER_API_KEY": "",
                    "GOOGLE_CLOUD_PROJECT": "",
                }
                run = lambda text: subprocess.run(
                    [sys.executable, "-m", "retail_assistant", "--thread", thread],
                    input=text,
                    text=True,
                    capture_output=True,
                    env=env,
                    timeout=15,
                )
                first = await asyncio.to_thread(run, "/delete phrase Client X\n/quit\n")
                self.assertEqual(first.returncode, 0, first.stderr)
                action = (await store.pending("analyst_a", thread))["id"]
                self.assertEqual(len(await store.reports("analyst_a")), 1)
                second = await asyncio.to_thread(
                    run, "/confirm " + action + "\n/history\n/quit\n"
                )
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertIn("Restored pending deletion", second.stdout)
                self.assertIn('"deleted": 1', second.stdout)
                self.assertIn("Retained history content", second.stdout)
                self.assertEqual(await store.reports("analyst_a"), [])
                third = await asyncio.to_thread(run, "/confirm " + action + "\n/quit\n")
                self.assertEqual(third.returncode, 0)
                self.assertIn('"deleted": 1', third.stdout)

    async def test_missing_model_does_not_crash_cli_or_block_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {
                **os.environ,
                "RUNTIME_DIR": temp,
                "OPENROUTER_API_KEY": "",
                "GOOGLE_CLOUD_PROJECT": "",
            }
            p = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-m", "retail_assistant"],
                input="Analyze April 2026\n/reports\n/quit\n",
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("model_configuration", p.stdout)
            self.assertNotIn("Traceback", p.stdout + p.stderr)
            logs = (Path(temp) / "events.jsonl").read_text()
            self.assertIn("model_step_failed", logs)
            self.assertNotIn("Analyze April", logs)

    async def test_configuration_and_redaction(self):
        from decimal import Decimal

        with self.assertRaises(Exception):
            Settings(budget_usd=Decimal("6"))
        text = scrub(
            "Email jane@example.com, phone +1 (555) 123-4567. Date 2026-04-01. sk-or-v1-12345678901234567890"
        )
        self.assertNotIn("jane@example.com", text)
        self.assertNotIn("123-4567", text)
        self.assertNotIn("12345678901234567890", text)
        self.assertIn("2026-04-01", text)

    async def test_iso_dates_next_to_years_are_not_phones_but_real_phones_still_mask(
        self,
    ):
        text = "April 2026 (2026-04-01 through 2026-04-30); phone +1 (555) 123-4567"
        result = scrub(text)
        self.assertIn("April 2026 (2026-04-01 through 2026-04-30)", result)
        self.assertNotIn("[REDACTED_PHONE]", result.split(";")[0])
        self.assertIn("[REDACTED_PHONE]", result.split(";")[1])
        self.assertNotIn("123-4567", result)
