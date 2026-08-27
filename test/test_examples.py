import pathlib
import subprocess
import sys
import unittest

EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent / "examples"


class TestCalculatorExample(unittest.TestCase):
    """
    Runs examples/calculator.py as an actual subprocess (not by importing it) so a regression in
    how it resolves paths/imports relative to the process's working directory -- exactly the kind
    of bug that slips by when a script is only ever read, not executed -- gets caught here.
    """

    def test_calculator_example_runs_from_repo_root(self):
        result = subprocess.run(
            [sys.executable, str(EXAMPLES_DIR / "calculator.py")],
            cwd=str(EXAMPLES_DIR.parent),
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertIn("added 1 and 2: 3", result.stdout)
        self.assertIn("subtracted 1 and 2: -1", result.stdout)

    def test_calculator_example_runs_from_examples_dir(self):
        result = subprocess.run(
            [sys.executable, "calculator.py"],
            cwd=str(EXAMPLES_DIR),
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        self.assertIn("added 1 and 2: 3", result.stdout)
        self.assertIn("subtracted 1 and 2: -1", result.stdout)


suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestCalculatorExample)
])
