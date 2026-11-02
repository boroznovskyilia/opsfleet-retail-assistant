import json
import unittest
from datetime import date
from importlib.resources import files

from retail_assistant.config import AppError
from retail_assistant.periods import extract, validate
from retail_assistant.policy import compile_query
from support import FixtureWarehouse

PERIOD = {"start": "2026-04-01", "end": "2026-04-30"}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.source = FixtureWarehouse()
        self.addCleanup(self.source.engine.dispose)

    def read(self, sql, owner="analyst_a"):
        return self.source.query(
            compile_query(sql), owner, PERIOD, "secret", lambda: 60, {"query_id": "q1"}
        )

    def test_all_educational_examples_compile(self):
        examples = json.loads(
            files("retail_assistant").joinpath("golden.json").read_text()
        )
        self.assertEqual(len(examples), 4)
        for example in examples:
            self.assertIn(
                "HAVING COUNT(DISTINCT customer_ref) >= 5",
                compile_query(example["sql"]).sql,
            )
            self.assertIn("Educational", example["provenance"])

    def test_small_group_suppression_before_limit(self):
        result = self.read(
            "SELECT state, SUM(amount) AS revenue FROM sales GROUP BY state ORDER BY revenue DESC LIMIT 1"
        )
        self.assertEqual(result["rows"], [{"state": "CA", "revenue": 100.0}])

    def test_mixed_products_correct_cohort_and_units(self):
        sql = "SELECT SUM(amount) AS revenue, COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT customer_ref) AS buyers, SAFE_DIVIDE(SUM(amount),COUNT(DISTINCT customer_ref)) AS spend_per_buyer, SAFE_DIVIDE(COUNT(DISTINCT order_id),COUNT(DISTINCT customer_ref)) AS order_frequency, SAFE_DIVIDE(SUM(amount),COUNT(DISTINCT order_id)) AS average_order_value FROM sales WHERE state='CA'"
        row = self.read(sql)["rows"][0]
        self.assertEqual(
            row,
            {
                "revenue": 100.0,
                "orders": 10,
                "buyers": 5,
                "spend_per_buyer": 20.0,
                "order_frequency": 2.0,
                "average_order_value": 10.0,
            },
        )
        self.assertEqual(
            row["spend_per_buyer"], row["order_frequency"] * row["average_order_value"]
        )
        self.assertEqual(self.read(sql, "analyst_b")["rows"][0]["revenue"], 10000)

    def test_customer_ranking_exception_and_scope(self):
        rows = self.read(
            "SELECT customer_ref, SUM(amount) AS revenue FROM sales GROUP BY customer_ref ORDER BY revenue DESC LIMIT 10"
        )["rows"]
        self.assertEqual(len(rows), 9)
        self.assertTrue(
            all(
                set(r) == {"customer_ref", "revenue"} and len(r["customer_ref"]) == 64
                for r in rows
            )
        )
        self.assertNotIn("secret@example.com", str(rows))
        with self.assertRaises(AppError):
            compile_query(
                "SELECT customer_ref,state,SUM(amount) AS revenue FROM sales GROUP BY customer_ref,state"
            )

    def test_attack_surface_rejected(self):
        attacks = [
            "DELETE FROM sales",
            "SELECT 1",
            "SELECT * FROM sales",
            "SELECT SUM(amount) AS revenue FROM sales; DELETE FROM sales",
            "WITH x AS (SELECT * FROM sales) SELECT SUM(amount) AS revenue FROM x",
            "SELECT SUM(amount) AS revenue FROM sales JOIN users USING(customer_ref)",
            "SELECT SUM(amount) AS revenue FROM `bigquery-public-data.thelook_ecommerce.order_items`",
            "SELECT SUM(amount) AS revenue FROM sales WHERE 1 IN (SELECT 1)",
            "SELECT SUM(amount) AS revenue FROM sales HAVING 1=1",
            "SELECT state,SUM(amount) AS revenue FROM sales GROUP BY state LIMIT 0",
            "SELECT state,SUM(amount) AS revenue FROM sales GROUP BY state LIMIT 1000",
            "SELECT SUM(amount) AS revenue FROM sales WHERE customer_ref='x'",
            "SELECT SUM(amount) AS revenue FROM sales WHERE EXTERNAL_QUERY('x','y')=1",
            "SELECT first_name,SUM(amount) AS revenue FROM sales GROUP BY first_name",
            "SELECT SUM(amount) AS revenue FROM sales ORDER BY RAND()",
            "SELECT SUM(amount) AS revenue FROM sales UNION ALL SELECT 1",
            "SELECT COUNT(*) AS buyers FROM sales",
            "SELECT state,SUM(amount) AS revenue FROM sales",
        ]
        for sql in attacks:
            with self.subTest(sql=sql), self.assertRaises(AppError):
                compile_query(sql)

    def test_quoted_literal_is_data_not_sql(self):
        query = compile_query(
            "SELECT SUM(amount) AS revenue FROM sales WHERE state='CA; DELETE FROM users'"
        )
        self.assertIn("'CA; DELETE FROM users'", query.sql)
        self.assertEqual(self.read(query.logical)["rows"], [])

    def test_aliases_month_and_empty(self):
        self.assertEqual(
            self.read(
                "SELECT DATE_TRUNC(s.sale_date,MONTH) AS month,SUM(s.amount) AS revenue FROM sales s GROUP BY month"
            )["rows"][0]["month"],
            "2026-04-01",
        )
        self.assertEqual(
            self.read("SELECT SUM(amount) AS revenue FROM sales WHERE state='absent'")[
                "rows"
            ],
            [],
        )

    def test_period_boundaries(self):
        self.assertEqual(extract("compare April 2026"), PERIOD)
        self.assertEqual(
            extract("Q1 2026"), {"start": "2026-01-01", "end": "2026-03-31"}
        )
        self.assertEqual(
            extract("last month", date(2026, 1, 2)),
            {"start": "2025-12-01", "end": "2025-12-31"},
        )
        self.assertIsNone(extract("compare states"))
        with self.assertRaises(AppError):
            validate("2026-04-30", "2026-04-01")
        for question in [
            "since 2026-04-01",
            "March through May 2026",
            "Q1 2026 versus Q2 2026",
            "April",
            "last 90 days",
        ]:
            with self.subTest(question=question), self.assertRaises(AppError):
                extract(question)

    def test_unclosed_literal_is_a_repairable_syntax_error(self):
        with self.assertRaises(AppError) as error:
            compile_query(
                "SELECT SUM(amount) AS revenue FROM sales WHERE state='unterminated"
            )
        self.assertEqual(error.exception.code, "invalid_sql")
