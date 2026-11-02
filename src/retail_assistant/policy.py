"""Deliberately narrow SQL surface; scope and support counts are code-owned."""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from .config import AppError
from .warehouse_sql import sales_source

DIMENSIONS = {
    name: name
    for name in (
        "product_id",
        "product_name",
        "category",
        "brand",
        "department",
        "state",
        "country",
        "sale_date",
    )
}
DIMENSIONS.update(
    month="DATE_TRUNC(sale_date, MONTH)",
    quarter="DATE_TRUNC(sale_date, QUARTER)",
    year="DATE_TRUNC(sale_date, YEAR)",
)
METRICS = {
    "revenue": "SUM(amount)",
    "orders": "COUNT(DISTINCT order_id)",
    "buyers": "COUNT(DISTINCT customer_ref)",
    "items": "COUNT(DISTINCT item_id)",
    "average_order_value": "SAFE_DIVIDE(SUM(amount), COUNT(DISTINCT order_id))",
    "order_frequency": "SAFE_DIVIDE(COUNT(DISTINCT order_id), COUNT(DISTINCT customer_ref))",
    "spend_per_buyer": "SAFE_DIVIDE(SUM(amount), COUNT(DISTINCT customer_ref))",
}
FILTER_COLUMNS = set(DIMENSIONS) - {"month", "quarter", "year"} | {"amount"}
PREDICATES = (
    exp.And,
    exp.Or,
    exp.Not,
    exp.Paren,
    exp.EQ,
    exp.NEQ,
    exp.GT,
    exp.GTE,
    exp.LT,
    exp.LTE,
    exp.In,
    exp.Between,
    exp.Like,
    exp.Is,
    exp.Column,
    exp.Identifier,
    exp.Literal,
    exp.Null,
    exp.Boolean,
    exp.Neg,
)


def canonical(node):
    value = node.copy()
    for col in value.find_all(exp.Column):
        col.set("table", None)
        col.set("this", exp.to_identifier(col.name.lower()))
    return value.sql(dialect="bigquery", normalize=True, comments=False)


def parsed(text):
    return sqlglot.parse_one(text, read="bigquery")


def deny(message="Only the documented flat sales SELECT/metric subset is allowed."):
    raise AppError("sql_policy", message)


@dataclass
class Query:
    logical: str
    sql: str
    ranking: bool
    limit: int | None
    columns: list[str]
    parameters: tuple = ()


# shortcut: flat grouped sales SQL only; add nested plans only with lineage/privacy checks.
def compile_query(sql: str) -> Query:
    if not isinstance(sql, str) or len(sql.encode()) > 12000:
        deny()
    try:
        statements = sqlglot.parse(sql, read="bigquery")
    except SqlglotError:
        raise AppError(
            "invalid_sql",
            "SQL could not be parsed; correct syntax without changing the question.",
        ) from None
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        deny()
    root = statements[0]
    if any(
        v and k not in {"expressions", "from_", "where", "group", "order", "limit"}
        for k, v in root.args.items()
    ):
        deny()
    tables = list(root.find_all(exp.Table))
    if len(list(root.find_all(exp.Select))) != 1 or len(tables) != 1:
        deny()
    table = tables[0]
    if table.name.lower() != "sales" or table.db or table.catalog:
        deny("Read only the scoped logical sales relation, never raw datasets.")
    if any(v and k not in {"this", "alias"} for k, v in table.args.items()):
        deny()
    if table.args.get("alias") and table.args["alias"].args.get("columns"):
        deny()
    alias = table.alias_or_name
    for col in root.find_all(exp.Column):
        if col.db or col.catalog or (col.table and col.table != alias):
            deny()
    projections, dimensions = {}, {}
    for item in root.expressions:
        name = item.alias_or_name.lower()
        value = item.this if isinstance(item, exp.Alias) else item
        if not name or name in projections or name.startswith("__"):
            deny()
        projections[name] = canonical(value)
        if name in DIMENSIONS and canonical(value) == canonical(
            parsed(DIMENSIONS[name])
        ):
            dimensions[name] = projections[name]
        elif name == "customer_ref" and canonical(value) == "customer_ref":
            dimensions[name] = "customer_ref"
        elif name not in METRICS or canonical(value) != canonical(
            parsed(METRICS[name])
        ):
            deny(
                "Use documented dimensions and exact metric formulas with their aliases."
            )
    if not projections or len(projections) > 10 or not set(projections) & set(METRICS):
        deny("Include at least one approved aggregate metric.")
    ranking = "customer_ref" in projections
    if ranking and set(projections) != {"customer_ref", "revenue"}:
        deny(
            "Individual customer ranking permits only customer_ref and SUM(amount) AS revenue."
        )
    group = root.args.get("group")
    grouped = set()
    if group:
        if any(v and k != "expressions" for k, v in group.args.items()):
            deny()
        for node in group.expressions:
            key = node.name.lower() if isinstance(node, exp.Column) else ""
            grouped.add(dimensions.get(key, canonical(node)))
    if grouped != set(dimensions.values()):
        deny("GROUP BY must exactly match the selected dimensions.")
    where = root.args.get("where")
    if where:
        for node in where.this.walk():
            if not isinstance(node, PREDICATES):
                deny(
                    "Filters allow simple comparisons/lists over approved nonprivate dimensions only."
                )
            if isinstance(node, exp.Column) and node.name.lower() not in FILTER_COLUMNS:
                deny(
                    "Customer/order/item identifiers cannot be used as filter predicates."
                )
    if root.args.get("order"):
        for item in root.args["order"].expressions:
            if (
                not isinstance(item.this, exp.Column)
                or item.this.name.lower() not in projections
            ):
                deny("ORDER BY must reference a selected output alias.")
    limit = None
    if root.args.get("limit"):
        expression = root.args["limit"].expression
        if (
            not isinstance(expression, exp.Literal)
            or expression.is_string
            or not expression.this.isdigit()
        ):
            deny()
        limit = int(expression.this)
        if not 1 <= limit <= 100:
            deny("Requested LIMIT must be between 1 and 100.")
    logical = root.sql(dialect="bigquery", comments=False)
    if not ranking:
        root = root.having(parsed("COUNT(DISTINCT customer_ref) >= 5"), copy=False)
    root = root.limit(limit or 101, copy=False)
    source, parameters = sales_source()
    scoped = parsed(source).subquery(alias=alias)
    table.replace(scoped)
    return Query(
        logical,
        root.sql(dialect="bigquery", comments=False),
        ranking,
        limit,
        list(projections),
        parameters,
    )


def schema():
    return {
        "relation": "sales (already scoped to user products, completed sales and explicit UTC period)",
        "dimensions": DIMENSIONS,
        "metrics": METRICS,
        "ranking": "SELECT customer_ref, SUM(amount) AS revenue FROM sales GROUP BY customer_ref ORDER BY revenue DESC LIMIT 10",
        "rules": "Exactly one flat SELECT. Use metric aliases and group every selected dimension. No joins/CTEs/subqueries/windows/HAVING. Code enforces the five-buyer rule, except the restricted customer ranking. Source: orders, order_items, products, users; raw PII is unavailable. Values are dataset sale-price units, not a verified FX/currency claim.",
    }
