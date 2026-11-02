"""English CLI; confirmation commands are parsed without any model call."""

import argparse
import asyncio
from contextlib import aclosing
import json
import signal
import sys

from . import periods
from .agent import Agent
from .config import AppError, Settings, USERS
from .llm import OpenRouter
from .services.reports import ReportService
from .store import Store
from .telemetry import configure, event
from .warehouse import BigQueryWarehouse

HELP = """Ask about permitted completed sales; specify a period or use /period.
/period YYYY-MM-DD YYYY-MM-DD    inclusive UTC analysis range
/new                            new independent conversation
/history                        show this owned conversation
/reports                        list owned saved reports
/save TITLE                     save the last assistant answer as a report
/delete phrase TEXT             preview all owned reports mentioning literal TEXT
/delete conversation            preview reports made in this conversation
/confirm ACTION_ID              delete the exact previewed library set
/reject [ACTION_ID]              reject, deleting nothing
/status                         local cumulative spend and pending action
/help                           commands
/quit                           exit; history and pending actions survive restart
Library deletion retains previously delivered chat history and exported copies.
"""


async def command(text, owner, thread, store):
    reports = ReportService(store, owner, thread)
    name, _, value = text.partition(" ")
    value = value.strip()
    if name == "/help":
        return thread, HELP
    if name == "/new":
        return (await store.thread(owner))[
            "id"
        ], "New conversation; no inherited analysis period."
    if name == "/period":
        values = value.split()
        if len(values) != 2:
            raise AppError("invalid_period", "Use /period YYYY-MM-DD YYYY-MM-DD.")
        chosen = periods.validate(*values)
        await store.period(owner, thread, chosen)
        return thread, "Analysis period: " + json.dumps(chosen) + " inclusive UTC."
    if name == "/history":
        return thread, "\n\n".join(
            m["role"] + ": " + m["body"] for m in await store.history(owner, thread)
        ) or "No messages yet."
    if name == "/reports":
        return thread, json.dumps(await reports.list(), indent=2)
    if name == "/status":
        return thread, json.dumps(
            {
                "spend": await store.spent(),
                "pending": await store.pending(owner, thread),
                "note": "Reservations include unknown/lost costs. Local records are not provider billing statements.",
            },
            indent=2,
        )
    if name == "/save":
        return thread, "Saved report: " + await reports.save_last(value)
    if name == "/delete":
        if value == "conversation":
            preview = await reports.prepare(conversation=True)
        elif value.startswith("phrase "):
            phrase = value[len("phrase ") :].strip()
            if len(phrase) >= 2 and phrase[0] == phrase[-1] and phrase[0] in {'"', "'"}:
                phrase = phrase[1:-1]
            preview = await reports.prepare(phrase=phrase)
        else:
            raise AppError(
                "invalid_selection", "Use /delete phrase TEXT or /delete conversation."
            )
        return thread, json.dumps(preview, indent=2)
    if name in {"/confirm", "/reject"}:
        return thread, json.dumps(await reports.decide(value, name[1:]), indent=2)
    raise AppError("unknown_command", "Unknown command; use /help.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="OpsFleet bounded retail analysis assistant"
    )
    parser.add_argument("--user", choices=USERS, default="analyst_a")
    parser.add_argument("--thread", help="Resume an owned conversation ID.")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check credentials/schema/model metadata without paid generation.",
    )
    args = parser.parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nConversation preserved.")
        return 130


def read_input():
    # The CLI is idle here; no DB session or external request stays open while typing.
    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        return input("\nYou> ")
    finally:
        signal.signal(signal.SIGINT, previous)


async def run(args):
    try:
        settings = Settings.load()
        configure(settings.runtime)
        warehouse = BigQueryWarehouse(settings)
        async with (
            Store(settings.runtime / "app.sqlite") as store,
            aclosing(OpenRouter(settings, store)) as model,
        ):
            try:
                return await chat(args, settings, store, warehouse, model)
            finally:
                await asyncio.to_thread(warehouse.close)
    except AppError as error:
        print("Error [" + error.code + "]: " + str(error), file=sys.stderr)
        return 1


async def chat(args, settings, store, warehouse, model):
    if args.doctor:
        failed = False
        for label, check in [
            ("BigQuery metadata", lambda: asyncio.to_thread(warehouse.doctor)),
            ("OpenRouter key/model metadata", model.doctor),
        ]:
            try:
                print(label + ": " + json.dumps(await check()))
            except AppError as error:
                print(label + ": " + error.code + " — " + str(error))
                failed = True
        return int(failed)
    thread = (await store.thread(args.user, args.thread))["id"]
    agent = Agent(
        settings,
        store,
        warehouse,
        model,
        lambda message: print("  " + message, flush=True),
    )
    print("OpsFleet | English prototype | demo user " + args.user)
    print(
        "Conversation: "
        + thread
        + "\nResume with --user "
        + args.user
        + " --thread "
        + thread
    )
    print(
        "Product scope: "
        + ("even" if USERS[args.user] == 0 else "odd")
        + " product IDs. /help for commands."
    )
    pending = await store.pending(args.user, thread)
    if pending:
        print(
            "Restored pending deletion (history is retained):\n"
            + json.dumps(pending, indent=2)
        )
    while True:
        try:
            raw = read_input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\nConversation preserved.")
            return 0
        if not raw:
            continue
        if raw == "/quit":
            return 0
        try:
            if raw.startswith("/"):
                thread, answer = await command(raw, args.user, thread, store)
                print(answer)
            else:
                result = await agent.turn(args.user, thread, raw)
                print(
                    "\nAssistant> "
                    + result["text"]
                    + "\nTrace request: "
                    + result["request_id"]
                )
        except AppError as error:
            print("Error [" + error.code + "]: " + str(error))
            event("request_failed", user=args.user, thread=thread, error=error.code)
        except Exception as error:
            event(
                "internal_error",
                user=args.user,
                thread=thread,
                error_class=type(error).__name__,
            )
            print(
                "An internal operation failed. Existing history and reports are preserved; see the local trace metadata."
            )


if __name__ == "__main__":
    raise SystemExit(main())
