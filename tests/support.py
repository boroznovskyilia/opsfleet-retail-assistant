"""Synthetic test-only data and scripted transport; never imported by production."""

import hashlib
import json
from datetime import date, timedelta

import sqlglot
from sqlglot import exp
from sqlalchemy import (
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
)
from sqlalchemy.pool import StaticPool

from retail_assistant.warehouse_sql import metadata as source_metadata

from retail_assistant.warehouse import JOB_BYTES


class FixtureWarehouse:
    def __init__(self):
        self.calls = []
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def functions(connection, record):
            connection.create_function("TIMESTAMP", 1, lambda value: value)
            connection.create_function(
                "S_H_A2_DIGEST",
                2,
                lambda value, bits: hashlib.sha256(value.encode()).digest(),
            )

            def truncate(unit, value):
                day = date.fromisoformat(value)
                month = (
                    1
                    if unit == "YEAR"
                    else ((day.month - 1) // 3) * 3 + 1
                    if unit == "QUARTER"
                    else day.month
                )
                return date(day.year, month, 1).isoformat()

            connection.create_function("DATE_TRUNC", 2, truncate)

        metadata = MetaData()
        tables = {
            table.name: Table(
                table.name,
                metadata,
                *[
                    Column(c.name, Text if isinstance(c.type, DateTime) else c.type)
                    for c in table.columns
                ],
            )
            for table in source_metadata.tables.values()
        }
        tables["users"].append_column(Column("first_name", String))
        tables["users"].append_column(Column("email", String))
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:

            def add(table_name, **values):
                connection.execute(tables[table_name].insert().values(**values))

            for product in [1, 2]:
                add(
                    "products",
                    id=product,
                    name="Odd product" if product == 1 else "Even product",
                    category="Category",
                    brand="Brand",
                    department="Department",
                )
            item = 0
            for buyer in range(1, 10):
                add(
                    "users",
                    id=buyer,
                    state="CA" if buyer <= 5 else "NY",
                    country="US",
                    first_name="SECRET_NAME",
                    email="secret@example.com",
                )
                for repeat in range(2 if buyer <= 5 else 1):
                    order = buyer * 10 + repeat
                    add("orders", order_id=order, user_id=buyer, status="Complete")
                    for product, amount in [(2, 10 if buyer <= 5 else 999), (1, 1000)]:
                        item += 1
                        add(
                            "order_items",
                            id=item,
                            order_id=order,
                            user_id=buyer,
                            product_id=product,
                            status="Complete",
                            created_at="2026-04-15",
                            returned_at=None,
                            sale_price=amount,
                        )
            add("orders", order_id=999, user_id=1, status="Complete")
            add("orders", order_id=998, user_id=1, status="Cancelled")
            for extra in [
                (1001, 999, 1, 2, "Returned", "2026-04-16", "2026-04-17", 100000),
                (1002, 998, 1, 2, "Complete", "2026-04-16", None, 100000),
                (1003, 999, 1, 2, "Complete", "2026-05-01", None, 100000),
            ]:
                add(
                    "order_items",
                    **dict(zip(tables["order_items"].columns.keys(), extra)),
                )

    def query(self, query, owner, period, secret, remaining, trace, scan_used=0):
        self.calls.append((owner, period, query))
        tree = sqlglot.parse_one(query.sql, read="bigquery")
        for table in tree.find_all(exp.Table):
            table.set("db", None)
            table.set("catalog", None)
        sql = tree.sql(dialect="sqlite")
        values = {
            "alias_secret": secret,
            "product_parity": 0 if owner == "analyst_a" else 1,
            "period_start": period["start"],
            "period_end": (
                date.fromisoformat(period["end"]) + timedelta(days=1)
            ).isoformat(),
        }
        values.update({name: value for name, kind, value in query.parameters})
        # Execute the generated analytical SQL itself to check its semantics.
        with self.engine.connect() as connection:
            rows = [dict(r) for r in connection.exec_driver_sql(sql, values).mappings()]
        return {
            "query_id": trace["query_id"],
            "sql": query.logical,
            "executed_sql": query.sql,
            "rows": rows[:100],
            "truncated": len(rows) > 100,
            "requested_limit": query.limit,
            "ranking_exception": query.ranking,
            "period": period,
            "scope": "even product IDs" if owner == "analyst_a" else "odd product IDs",
            "scan_reservation": JOB_BYTES,
            "scan_bytes": 100,
            "job_id": "synthetic-test-job",
        }

    def catalog(self, owner, remaining):
        return {
            "rows": [{"product_id": 2 if owner == "analyst_a" else 1}],
            "subset": True,
        }


def calls(*items):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_" + str(i),
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
            for i, (name, args) in enumerate(items)
        ],
    }


def answer(
    summary="Completed sales evidence is shown above.", ids=None, kind="analysis"
):
    return {
        "role": "assistant",
        "content": json.dumps(
            {
                "kind": kind,
                "summary": summary,
                "hypotheses": [
                    "A frequency difference could be investigated; it is not a proven cause."
                ]
                if kind == "analysis"
                else [],
                "actions": ["Compare matched periods before testing an intervention."]
                if kind == "analysis"
                else [],
                "evidence_ids": ids or [],
            }
        ),
    }


class ScriptedModel:
    def __init__(self, *steps):
        self.steps = list(steps)
        self.inputs = []
        self.allowed_tools = []

    async def call(self, messages, tools, remaining, trace, response_format):
        self.inputs.append(messages)
        self.allowed_tools.append(tools)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step
