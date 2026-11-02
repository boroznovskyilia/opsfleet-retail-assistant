"""Async owned state; each operation owns one short session and transaction."""

import hashlib
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from uuid import uuid4

from sqlalchemy import URL, case, delete, event, func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import AppError, USERS
from .models import Action, Base, Message, Report, Setting, Spend, Thread


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid4().hex[:16]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def micros(value):
    return int(
        (Decimal(str(value)) * 1_000_000).to_integral_value(rounding=ROUND_CEILING)
    )


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
        self.engine = create_async_engine(
            URL.create("sqlite+aiosqlite", database=str(path)),
            connect_args={"timeout": 5},
            hide_parameters=True,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        event.listen(self.engine.sync_engine, "connect", self._connect)
        event.listen(self.engine.sync_engine, "begin", self._begin)

    @staticmethod
    def _connect(connection, record):
        connection.isolation_level = None

    @staticmethod
    def _begin(connection):
        # SQLite has no row locks; lock before read/check/write, including across processes.
        connection.exec_driver_sql(
            "BEGIN IMMEDIATE"
            if connection.get_execution_options().get("sqlite_write")
            else "BEGIN"
        )

    async def __aenter__(self):
        try:
            async with self.session(write=True) as session:
                connection = await session.connection()
                await connection.run_sync(Base.metadata.create_all)
                await session.execute(
                    insert(Setting)
                    .values(key="alias_secret", value=secrets.token_hex(32))
                    .on_conflict_do_nothing(index_elements=[Setting.key])
                )
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self, *, write=False):
        try:
            async with self.sessions.begin() as session:
                await session.connection(execution_options={"sqlite_write": write})
                yield session
        except SQLAlchemyError:
            raise AppError(
                "storage_unavailable",
                "Local storage failed or is busy; the operation was rolled back. Retry without resetting the database.",
            ) from None

    @staticmethod
    def _user(owner):
        if owner not in USERS:
            raise AppError("unknown_user", "Choose analyst_a or analyst_b.")

    async def _thread(self, session, owner, thread_id):
        self._user(owner)
        row = await session.scalar(
            select(Thread).where(Thread.id == thread_id, Thread.owner == owner)
        )
        if row is None:
            raise AppError("thread_not_found", "Unknown conversation for this user.")
        return row

    async def thread(self, owner, thread_id=None):
        self._user(owner)
        async with self.session(write=thread_id is None) as session:
            if thread_id is None:
                row = Thread(id=uid(), owner=owner)
                session.add(row)
            else:
                row = await self._thread(session, owner, thread_id)
            return {"id": row.id, "owner": row.owner, "period": row.period}

    async def secret(self, owner):
        self._user(owner)
        async with self.session() as session:
            value = await session.scalar(
                select(Setting.value).where(Setting.key == "alias_secret")
            )
            return digest(value + ":" + owner)

    async def period(self, owner, thread, value=None):
        async with self.session(write=value is not None) as session:
            row = await self._thread(session, owner, thread)
            if value is not None:
                row.period = value
            return row.period

    async def append(self, owner, thread, role, body):
        async with self.session(write=True) as session:
            await self._thread(session, owner, thread)
            session.add(Message(thread=thread, role=role, body=body, created=now()))

    async def history(self, owner, thread):
        async with self.session() as session:
            await self._thread(session, owner, thread)
            rows = await session.execute(
                select(Message.role, Message.body)
                .where(Message.thread == thread)
                .order_by(Message.id)
            )
            return [dict(row) for row in rows.mappings()]

    async def save(self, owner, thread, title, body):
        if not title.strip() or not body.strip():
            raise AppError("invalid_report", "A report needs a title and content.")
        report_id, title = uid(), title[:100]
        async with self.session(write=True) as session:
            await self._thread(session, owner, thread)
            session.add(
                Report(
                    id=report_id,
                    owner=owner,
                    thread=thread,
                    title=title,
                    body=body,
                    hash=digest(title + "\n" + body),
                    created=now(),
                )
            )
        return report_id

    async def reports(self, owner):
        self._user(owner)
        async with self.session() as session:
            rows = await session.execute(
                select(Report.__table__)
                .where(Report.owner == owner)
                .order_by(Report.created, Report.id)
            )
            return [dict(row) for row in rows.mappings()]

    async def prepare(self, owner, thread, phrase=None, conversation=False):
        if not conversation and (not isinstance(phrase, str) or not phrase.strip()):
            raise AppError(
                "invalid_selection",
                "Specify a nonempty literal phrase or the current conversation.",
            )
        async with self.session(write=True) as session:
            await self._thread(session, owner, thread)
            rows = await session.scalars(
                select(Report)
                .where(Report.owner == owner)
                .order_by(Report.created, Report.id)
            )
            selected = [
                r
                for r in rows
                if (
                    r.thread == thread
                    if conversation
                    else phrase.casefold() in (r.title + "\n" + r.body).casefold()
                )
            ]
            if not selected:
                return {
                    "id": None,
                    "reports": [],
                    "notice": "No matching owned reports; nothing to delete.",
                }
            action = uid()
            await session.execute(
                update(Action)
                .where(
                    Action.owner == owner,
                    Action.thread == thread,
                    Action.status == "pending",
                )
                .values(status="superseded")
            )
            frozen = [{"id": r.id, "hash": r.hash, "title": r.title} for r in selected]
            session.add(
                Action(
                    id=action,
                    owner=owner,
                    thread=thread,
                    status="pending",
                    selection=frozen,
                    created=now(),
                )
            )
            preview = [{"id": r.id, "title": r.title} for r in selected]
        return {
            "id": action,
            "reports": preview,
            "notice": "Deletes library reports only. Chat history and exported copies remain. Confirm the exact set with /confirm "
            + action
            + "; reject with /reject "
            + action,
        }

    async def pending(self, owner, thread):
        async with self.session() as session:
            await self._thread(session, owner, thread)
            row = await session.scalar(
                select(Action).where(
                    Action.owner == owner,
                    Action.thread == thread,
                    Action.status == "pending",
                )
            )
            return {"id": row.id, "reports": row.selection} if row else None

    async def decide(self, owner, thread, action, decision):
        if decision not in {"confirm", "reject"}:
            raise AppError("invalid_decision", "Use confirm or reject.")
        desired = "confirmed" if decision == "confirm" else "rejected"
        async with self.session(write=True) as session:
            await self._thread(session, owner, thread)
            row = await session.scalar(
                select(Action).where(
                    Action.id == action, Action.owner == owner, Action.thread == thread
                )
            )
            if row is None:
                raise AppError(
                    "action_not_found", "Unknown action in this conversation."
                )
            if row.status == desired:
                return row.receipt
            if row.status != "pending":
                raise AppError(
                    "action_conflict", "Action was already decided or superseded."
                )
            selected = row.selection
            if decision == "confirm":
                ids = [item["id"] for item in selected]
                reports = {
                    r.id: r
                    for r in await session.scalars(
                        select(Report).where(Report.id.in_(ids), Report.owner == owner)
                    )
                }
                for item in selected:
                    report = reports.get(item["id"])
                    if (
                        report is None
                        or report.title != item["title"]
                        or report.hash != item["hash"]
                        or digest(report.title + "\n" + report.body) != item["hash"]
                    ):
                        raise AppError(
                            "stale_selection",
                            "The preview changed; prepare and confirm a new selection.",
                        )
                await session.execute(
                    delete(Report).where(Report.id.in_(ids), Report.owner == owner)
                )
            receipt = {
                "action_id": action,
                "status": desired,
                "deleted": len(selected) if decision == "confirm" else 0,
                "history_retained": True,
            }
            row.status, row.receipt = desired, receipt
            return receipt

    async def reserve(self, amount, ceiling):
        amount, ceiling = micros(amount), micros(ceiling)
        async with self.session(write=True) as session:
            used = await session.scalar(
                select(func.coalesce(func.sum(Spend.micros), 0))
            )
            if amount <= 0 or used + amount > ceiling:
                raise AppError(
                    "model_budget",
                    "Cumulative model budget exhausted; no paid request was sent.",
                )
            key = uid()
            session.add(Spend(id=key, micros=amount, status="reserved", created=now()))
            return key

    async def settle(self, key, cost):
        value = Decimal(str(cost))
        if not value.is_finite() or value < 0:
            raise AppError(
                "unknown_cost",
                "Provider cost unavailable; reservation remains charged.",
            )
        async with self.session(write=True) as session:
            row = await session.get(Spend, key)
            if row is None or row.status != "reserved":
                raise AppError(
                    "invalid_reservation", "Unknown or settled model reservation."
                )
            overrun = micros(value) > row.micros
            row.micros, row.status = micros(value), "overrun" if overrun else "settled"
        if overrun:
            raise AppError(
                "price_overrun",
                "Provider exceeded reserved price; further paid requests are disabled.",
            )

    async def spent(self):
        async with self.session() as session:
            result = (
                (
                    await session.execute(
                        select(
                            (
                                func.coalesce(func.sum(Spend.micros), 0) / 1_000_000.0
                            ).label("usd"),
                            func.coalesce(
                                func.sum(case((Spend.status == "overrun", 1), else_=0)),
                                0,
                            ).label("overruns"),
                        )
                    )
                )
                .mappings()
                .one()
            )
            return dict(result)
