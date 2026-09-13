import json
import unittest
from pathlib import Path
from unittest.mock import patch

from Stl2StepFusion import engine


class ParseResultTests(unittest.TestCase):
    def test_uses_last_result_line(self):
        result = engine.parse_result(
            'progress\nRESULT {"ok": false}\nRESULT {"ok": true, "solids": 1}\n'
        )
        self.assertEqual(result, {"ok": True, "solids": 1})

    def test_rejects_missing_result(self):
        with self.assertRaises(engine.EngineError):
            engine.parse_result("converter output without a result")


class ConvertTests(unittest.TestCase):
    def test_rejects_unknown_units_and_modes_before_spawning(self):
        executable = Path("stl2step.exe")
        with self.assertRaises(ValueError):
            engine.convert(executable, Path("input.stl"), Path("output.step"), units="cm")
        with self.assertRaises(ValueError):
            engine.convert(
                executable, Path("input.stl"), Path("output.step"), units="mm", mode="unknown"
            )

    @patch("Stl2StepFusion.engine.subprocess.run")
    def test_accepts_warning_exit_code_when_step_exists(self, run):
        output = Path("output.step")
        run.return_value.returncode = 2
        run.return_value.stdout = 'RESULT ' + json.dumps({"ok": True, "warnings": ["open shell"]})
        run.return_value.stderr = ""
        with patch.object(Path, "is_file", return_value=True):
            result = engine.convert(Path("stl2step.exe"), Path("input.stl"), output, units="mm")
        self.assertTrue(result["ok"])
        self.assertEqual(run.call_args.args[0][-2:], ["--units", "mm"])


if __name__ == "__main__":
    unittest.main()
