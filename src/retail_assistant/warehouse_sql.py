"""Trusted BigQuery projections built with Core; no database connection is created."""

import sqlglot
from sqlglot import exp
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    bindparam,
    cast,
    func,
    select,
)
from sqlalchemy_bigquery import BigQueryDialect

metadata = MetaData(schema="bigquery-public-data.thelook_ecommerce")
orders = Table(
    "orders",
    metadata,
    Column("order_id", Integer),
    Column("user_id", Integer),
    Column("status", String),
)
items = Table(
    "order_items",
    metadata,
    Column("id", Integer),
    Column("order_id", Integer),
    Column("user_id", Integer),
    Column("product_id", Integer),
    Column("status", String),
    Column("created_at", DateTime),
    Column("returned_at", DateTime),
    Column("sale_price", Float),
)
products = Table(
    "products",
    metadata,
    Column("id", Integer),
    *[Column(name, String) for name in ("name", "category", "brand", "department")],
)
users = Table(
    "users",
    metadata,
    Column("id", Integer),
    Column("state", String),
    Column("country", String),
)


def compile_sql(statement):
    compiled = statement.compile(dialect=BigQueryDialect(paramstyle="named"))
    tree = sqlglot.parse_one(str(compiled), read="bigquery")
    # The SDK uses @name, while SQLAlchemy's named compiler emits :name.
    for placeholder in list(tree.find_all(exp.Placeholder)):
        placeholder.replace(exp.Parameter(this=exp.Var(this=placeholder.name)))
    parameters = tuple(
        (name, compiled.dialect.type_compiler.process(compiled.binds[name].type), value)
        for name, value in compiled.params.items()
        if not compiled.binds[name].required
    )
    return tree.sql(dialect="bigquery"), parameters


def sales_source():
    oi, o, p, u = (
        items.alias("oi"),
        orders.alias("o"),
        products.alias("p"),
        users.alias("u"),
    )
    return compile_sql(
        select(
            func.DATE(oi.c.created_at, "UTC").label("sale_date"),
            oi.c.product_id,
            p.c.name.label("product_name"),
            p.c.category,
            p.c.brand,
            p.c.department,
            u.c.state,
            u.c.country,
            oi.c.order_id,
            oi.c.id.label("item_id"),
            func.TO_HEX(
                func.SHA256(
                    func.CONCAT(
                        bindparam("alias_secret", type_=String),
                        ":",
                        cast(oi.c.user_id, String),
                    )
                )
            ).label("customer_ref"),
            cast(oi.c.sale_price, Numeric).label("amount"),
        )
        .select_from(
            oi.join(o, and_(o.c.order_id == oi.c.order_id, o.c.user_id == oi.c.user_id))
            .join(p, p.c.id == oi.c.product_id)
            .join(u, u.c.id == oi.c.user_id)
        )
        .where(
            func.MOD(oi.c.product_id, 2) == bindparam("product_parity", type_=Integer),
            o.c.status == "Complete",
            oi.c.status == "Complete",
            oi.c.returned_at.is_(None),
            oi.c.created_at >= func.TIMESTAMP(bindparam("period_start", type_=String)),
            oi.c.created_at < func.TIMESTAMP(bindparam("period_end", type_=String)),
        )
    )


def product_catalog():
    product = products.alias("p")
    return compile_sql(
        select(
            product.c.id.label("product_id"),
            product.c.name.label("product_name"),
            product.c.category,
            product.c.brand,
            product.c.department,
        )
        .where(func.MOD(product.c.id, 2) == bindparam("parity", type_=Integer))
        .order_by(product.c.id)
        .limit(50)
    )
