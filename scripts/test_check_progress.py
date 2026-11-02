import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from check_progress import validate


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.plan = "- T01.1 Review\n- T02.1 Build\n"
        self.state = {
            "schema_version": 1,
            "updated_at": "2026-10-31T10:00:00+00:00",
            "authorization": {
                "project_work": "authorized",
                "evidence": "Owner instruction",
            },
            "current_task": "T02.1",
            "next_action": "Build the locked environment",
            "last_checks": [
                {"command": "make check", "result": "passed", "scope": "Documentation"}
            ],
            "blockers": [],
            "tasks": [
                {
                    "id": "T01.1",
                    "status": "done",
                    "evidence": ["Reviewed spec"],
                    "blocker": None,
                },
                {
                    "id": "T02.1",
                    "status": "in_progress",
                    "evidence": [],
                    "blocker": None,
                },
            ],
        }

    def test_valid_resume_and_completed_task(self):
        self.assertEqual(len(validate(self.state, self.plan)), 2)
        self.state["tasks"][1].update(status="done", evidence=["Tests passed"])
        self.state["current_task"] = None
        validate(self.state, self.plan)

    def test_inventory_drift_and_duplicate_fail(self):
        for tasks in (self.state["tasks"][:1], self.state["tasks"] * 2):
            state = deepcopy(self.state)
            state["tasks"] = tasks
            with self.assertRaises(ValueError):
                validate(state, self.plan)

    def test_done_requires_evidence_and_blocked_requires_reason(self):
        self.state["tasks"][0]["evidence"] = []
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)
        self.state["tasks"][0].update(status="blocked", blocker="Missing decision")
        validate(self.state, self.plan)
        self.state["tasks"][0]["blocker"] = None
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)

    def test_unrecorded_authorization_and_wrong_current_task_fail(self):
        self.state["authorization"]["project_work"] = "not_authorized"
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)
        self.state["authorization"]["project_work"] = "authorized"
        self.state["current_task"] = None
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)

    def test_fresh_process_reads_saved_state_and_rejects_corruption(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/plans").mkdir(parents=True)
            (root / "docs/plans/implementation.md").write_text(self.plan)
            progress = root / "docs/plans/progress.json"
            state = deepcopy(self.state)
            state["blockers"] = []
            progress.write_text(json.dumps(state))
            command = [
                sys.executable,
                str(Path(__file__).with_name("check_progress.py")),
                str(root),
            ]
            restored = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertIn("Current task: T02.1", restored.stdout)
            self.assertIn("done=1", restored.stdout)
            progress.write_text("{broken")
            broken = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(broken.returncode, 1)
            self.assertIn("Invalid progress state", broken.stderr)

    def test_unknown_status_and_false_check_result_fail(self):
        self.state["tasks"][1]["status"] = "almost_done"
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)
        self.state["tasks"][1]["status"] = "in_progress"
        self.state["last_checks"][0]["result"] = "probably_passed"
        with self.assertRaises(ValueError):
            validate(self.state, self.plan)

    def test_empty_seed_requires_no_project_authorization(self):
        state = deepcopy(self.state)
        state.update(tasks=[], current_task=None, last_checks=[])
        state["authorization"]["project_work"] = "not_authorized"
        self.assertEqual(validate(state, "# No project tasks yet\n"), [])

    def test_first_task_has_no_implicit_authorization_exemption(self):
        state = deepcopy(self.state)
        state["tasks"] = state["tasks"][:1]
        state["tasks"][0]["status"] = "in_progress"
        state["current_task"] = "T01.1"
        state["authorization"]["project_work"] = "not_authorized"
        with self.assertRaises(ValueError):
            validate(state, "- T01.1 First owner task\n")
        state["authorization"]["project_work"] = "authorized"
        validate(state, "- T01.1 First owner task\n")

    def test_blocked_question_allows_independent_task_progress(self):
        state = deepcopy(self.state)
        state["tasks"][0].update(
            status="blocked",
            blocker="Which accepted rule applies? Options A/B; impact recorded.",
        )
        validate(state, self.plan)
        state["tasks"][1].update(status="not_started")
        state["current_task"] = None
        validate(state, self.plan)

    def test_duplicate_plan_ids_are_rejected(self):
        state = deepcopy(self.state)
        state["tasks"] = [deepcopy(state["tasks"][0])] * 2
        state["current_task"] = None
        with self.assertRaises(ValueError):
            validate(state, "- T01.1 First\n- T01.1 Duplicate\n")


if __name__ == "__main__":
    unittest.main()
