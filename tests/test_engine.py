import json
import threading
import subprocess
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

    @patch("Stl2StepFusion.engine._run_conversion_process")
    def test_accepts_warning_exit_code_when_step_exists(self, run):
        output = Path("output.step")
        run.return_value = subprocess.CompletedProcess(
            [], 2, 'RESULT ' + json.dumps({"ok": True, "warnings": ["open shell"]}), ""
        )
        with patch.object(Path, "is_file", return_value=True):
            result = engine.convert(Path("stl2step.exe"), Path("input.stl"), output, units="mm")
        self.assertTrue(result["ok"])
        self.assertEqual(run.call_args.args[0][-2:], ["--units", "mm"])

    @patch("Stl2StepFusion.engine._run_conversion_process")
    def test_passes_verbatim_mode_to_engine(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, 'RESULT ' + json.dumps({"ok": True}), ""
        )
        with patch.object(Path, "is_file", return_value=True):
            engine.convert(
                Path("stl2step.exe"), Path("input.stl"), Path("output.step"),
                units="in", mode="verbatim",
            )
        command = run.call_args.args[0]
        self.assertEqual(command[-4:], ["--engine", "verbatim", "--units", "in"])

    @patch("Stl2StepFusion.engine._run_conversion_process")
    def test_reports_stderr_when_result_is_missing(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "native failure")
        with self.assertRaisesRegex(engine.EngineError, "native failure"):
            engine.convert(
                Path("stl2step.exe"), Path("input.stl"), Path("output.step"), units="mm"
            )

    @patch("Stl2StepFusion.engine._run_conversion_process")
    def test_rejects_success_without_step_output(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, 'RESULT ' + json.dumps({"ok": True}), ""
        )
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(engine.EngineError, "STEP file is missing"):
                engine.convert(
                    Path("stl2step.exe"), Path("input.stl"), Path("output.step"), units="mm"
                )

    @patch("Stl2StepFusion.engine.time.sleep")
    @patch("Stl2StepFusion.engine.subprocess.Popen")
    def test_cancellation_terminates_the_child_process(self, popen, _sleep):
        class FakeProcess:
            returncode = None

            def poll(self):
                return self.returncode

            def terminate(self):
                self.returncode = 1

            def wait(self, timeout=None):
                return self.returncode

            def kill(self):
                self.returncode = -9

            def communicate(self):
                return "", ""

        process = FakeProcess()
        popen.return_value = process
        cancel_event = threading.Event()
        cancel_event.set()
        with self.assertRaises(engine.EngineCancelled):
            engine._run_conversion_process(["stl2step.exe"], cancel_event=cancel_event)
        self.assertEqual(process.returncode, 1)


if __name__ == "__main__":
    unittest.main()
