import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import sqlglot
from sqlglot import exp

from retail_assistant.config import AppError, Settings
from retail_assistant.policy import compile_query
from retail_assistant.warehouse import BigQueryWarehouse, EXPECTED, JOB_BYTES


class Job:
    state = "DONE"
    total_bytes_processed = 100
    job_id = "fake-sdk-job"

    def result(self, **kwargs):
        self.result_kwargs = kwargs
        return [{"revenue": 10}]


class Client:
    def __init__(self, estimate=100):
        self.estimate = estimate
        self.calls = []

    def get_dataset(self, *args, **kwargs):
        return SimpleNamespace(location="US")

    def get_table(self, name, **kwargs):
        return SimpleNamespace(
            schema=[SimpleNamespace(name=k) for k in EXPECTED[name.rsplit(".", 1)[-1]]]
        )

    def query(self, sql, **kwargs):
        self.calls.append((sql, kwargs))
        job = Job()
        job.total_bytes_processed = self.estimate
        return job


class WarehouseTests(unittest.TestCase):
    def test_expired_catalog_cannot_start_metadata_or_query(self):
        warehouse = BigQueryWarehouse(Settings(project="test"))
        warehouse.client = Mock()
        with self.assertRaises(AppError) as error:
            warehouse.catalog("analyst_a", lambda: 0)
        self.assertEqual(error.exception.code, "turn_budget")
        warehouse.client.get_dataset.assert_not_called()
        warehouse.client.query.assert_not_called()

    def test_real_sdk_job_configs_scope_and_hard_limit(self):
        warehouse = BigQueryWarehouse(Settings(project="synthetic-test-project"))
        warehouse.client = Client()
        result = warehouse.query(
            compile_query("SELECT SUM(amount) AS revenue FROM sales"),
            "analyst_a",
            {"start": "2026-04-01", "end": "2026-04-30"},
            "never-log-secret",
            lambda: 60,
            {"query_id": "q1"},
        )
        self.assertEqual(len(warehouse.client.calls), 2)
        dry = warehouse.client.calls[0][1]["job_config"]
        real = warehouse.client.calls[1][1]["job_config"]
        self.assertTrue(dry.dry_run)
        self.assertFalse(dry.use_query_cache)
        self.assertEqual(real.maximum_bytes_billed, JOB_BYTES)
        parameters = {p.name: p.value for p in real.query_parameters}
        self.assertEqual(parameters["period_end"], "2026-05-01")
        self.assertEqual(parameters["product_parity"], 0)
        placeholders = {
            p.name
            for p in sqlglot.parse_one(
                warehouse.client.calls[1][0], read="bigquery"
            ).find_all(exp.Parameter)
        }
        self.assertEqual(placeholders, set(parameters))
        self.assertEqual(parameters["status_1"], "Complete")
        self.assertNotIn("never-log-secret", str(result))

    def test_core_catalog_compilation_and_bound_parameters(self):
        warehouse = BigQueryWarehouse(Settings(project="test"))
        warehouse.client = Client()
        warehouse.catalog("analyst_b", lambda: 60)
        sql, options = warehouse.client.calls[0]
        tree = sqlglot.parse_one(sql, read="bigquery")
        source = tree.find(exp.Table)
        self.assertTrue(source.alias)
        self.assertTrue(all(c.table == source.alias for c in tree.find_all(exp.Column)))
        parameters = {p.name: p.value for p in options["job_config"].query_parameters}
        placeholders = {
            p.name
            for p in sqlglot.parse_one(sql, read="bigquery").find_all(exp.Parameter)
        }
        self.assertEqual(placeholders, set(parameters))
        self.assertEqual(parameters, {"parity": 1, "MOD_1": 2, "param_1": 50})
        self.assertEqual(options["job_config"].maximum_bytes_billed, JOB_BYTES)

    def test_dry_run_excess_never_executes(self):
        warehouse = BigQueryWarehouse(Settings(project="test"))
        warehouse.client = Client(JOB_BYTES + 1)
        with self.assertRaises(AppError) as e:
            warehouse.query(
                compile_query("SELECT SUM(amount) AS revenue FROM sales"),
                "analyst_a",
                {"start": "2026-04-01", "end": "2026-04-30"},
                "secret",
                lambda: 60,
                {"query_id": "q1"},
            )
        self.assertEqual(e.exception.code, "scan_budget")
        self.assertEqual(len(warehouse.client.calls), 1)
