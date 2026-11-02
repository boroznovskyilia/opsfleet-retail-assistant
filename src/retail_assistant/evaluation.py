"""Separate local mechanics from explicitly requested real-provider review evidence."""

import argparse
import asyncio
from contextlib import aclosing
import hashlib
import json
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from .agent import Agent
from .config import AppError, Settings, USERS
from .llm import OpenRouter
from .periods import validate
from .store import Store
from .telemetry import configure
from .warehouse import BigQueryWarehouse


def fingerprint():
    digest = hashlib.sha256()
    for path in sorted(
        [
            *Path("src").rglob("*.py"),
            *Path("src").rglob("*.json"),
            *Path("tests").rglob("*.py"),
            *Path("tests/fixtures").glob("*"),
            Path("pyproject.toml"),
            Path("uv.lock"),
        ]
    ):
        digest.update(str(path).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use real credentials and shared USD 5 ledger; outputs require review.",
    )
    parser.add_argument(
        "--start", help="Inclusive YYYY-MM-DD; required for live analysis."
    )
    parser.add_argument(
        "--end", help="Inclusive YYYY-MM-DD; required for live analysis."
    )
    parser.add_argument("--user", choices=USERS, default="analyst_a")
    args = parser.parse_args(argv)
    settings = Settings.load()
    folder = settings.runtime / "evaluation"
    folder.mkdir(parents=True, exist_ok=True)
    report = {
        "created": datetime.now(timezone.utc).isoformat(),
        "layer": "live_review" if args.live else "local_mechanics",
        "source_sha256": fingerprint(),
        "model": settings.model,
    }
    if not args.live:
        suite = unittest.defaultTestLoader.discover("tests")
        if not suite.countTestCases():
            print(
                "No local tests found; run from the repository root.", file=sys.stderr
            )
            return 1
        result = unittest.TextTestRunner(verbosity=1, stream=sys.stdout).run(suite)
        report.update(
            tests=result.testsRun,
            failures=len(result.failures),
            errors=len(result.errors),
            passed=result.wasSuccessful(),
            live_quality="not_run",
        )
        destination = folder / "local-results.json"
        status = 0 if result.wasSuccessful() else 1
    else:
        if not args.start or not args.end:
            parser.error(
                "--live requires --start and --end; no default period is allowed"
            )
        period = validate(args.start, args.end)
        asyncio.run(live(settings, args, period, report))
        destination = folder / (
            "live-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
        )
        status = 2
    destination.write_text(json.dumps(report, indent=2, default=str) + "\n")
    destination.chmod(0o600)
    print("Evidence: " + str(destination))
    return status


async def live(settings, args, period, report):
    configure(settings.runtime)
    warehouse = BigQueryWarehouse(settings)
    async with (
        Store(settings.runtime / "app.sqlite") as store,
        aclosing(OpenRouter(settings, store)) as model,
    ):
        try:
            await asyncio.to_thread(warehouse.doctor)
            await model.doctor()
            agent = Agent(settings, store, warehouse, model)
            questions = [
                "Compare completed sales and spending per active buyer by state",
                "Show monthly revenue and explain limitations of the trend",
                "Create a report comparing permitted product performance with hypotheses and action items",
            ]
            report["cases"] = []
            for index, question in enumerate(questions, 1):
                thread = (await store.thread(args.user))["id"]
                started = time.monotonic()
                response = await agent.turn(
                    args.user,
                    thread,
                    question + " from " + period["start"] + " through " + period["end"],
                )
                report["cases"].append(
                    {
                        "id": "live-" + str(index),
                        "question": question,
                        "thread": thread,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "status": "review_required",
                        "response": response,
                    }
                )
            report["note"] = (
                "Real outputs are retained for source-grounded human review; no automatic correctness score is asserted. Do not reuse educational methods as answer oracles."
            )
            report["spend"] = await store.spent()
        finally:
            await asyncio.to_thread(warehouse.close)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AppError as error:
        print(error.code + ": " + str(error), file=sys.stderr)
        raise SystemExit(1)
