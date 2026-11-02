import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retail_assistant.config import Settings
from retail_assistant.evaluation import main


class EvaluationTests(unittest.TestCase):
    def test_live_needs_explicit_period_before_any_integration(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch(
                "retail_assistant.evaluation.Settings.load",
                return_value=Settings(runtime=Path(temp)),
            ),
            patch("sys.stderr", new_callable=io.StringIO),
        ):
            with self.assertRaises(SystemExit) as exit_code:
                main(["--live"])
            self.assertEqual(exit_code.exception.code, 2)
            self.assertFalse((Path(temp) / "app.sqlite").exists())
