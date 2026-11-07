"""Resume after a crash: paid trials are kept, only missing trials are run, and nothing is overwritten.

Drives the real CLI with a stand-in `anthropic` module on PYTHONPATH (no network, fake key).
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE_SDK = textwrap.dedent('''
    import json, os
    __version__ = "fake"
    class _B:
        def __init__(self, **k): self.__dict__.update(k)
        def model_dump(self, mode="json"): return dict(self.__dict__)
    class _U:
        input_tokens, output_tokens = 100, 10
        cache_creation_input_tokens = cache_read_input_tokens = 0
    class _R:
        def __init__(self, content, stop):
            self.content, self.stop_reason = content, stop
            self.id, self.model, self.usage, self.stop_details = "msg", "fake", _U(), None
    class Anthropic:
        def __init__(self, **kw): self.messages = self
        def create(self, **kw):
            log = os.environ["FAKE_CALL_LOG"]
            with open(log, "a") as f: f.write("call\\n")
            n = sum(1 for _ in open(log))
            if n > int(os.environ.get("FAKE_FAIL_AFTER", "999999")):
                raise TimeoutError("simulated network timeout")
            return _R([_B(type="text", text="done")], "end_turn")
''')


class TestResume(unittest.TestCase):
    def run_cli(self, tmp, out, extra_env):
        env = {**os.environ, "PYTHONPATH": f"{tmp}/sdk:{ROOT}", "ANTHROPIC_API_KEY": "fake",
               "FAKE_CALL_LOG": f"{tmp}/calls.log", **extra_env}
        return subprocess.run([sys.executable, "-m", "boundarybench", "run", "--agent", "anthropic",
                               "--model", "claude-haiku-5-5", "--limit", "4", "--mode", "instruction_only",
                               "--out", str(out)], cwd=ROOT, env=env, capture_output=True, text=True)

    def test_crash_then_resume_keeps_paid_trials(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "sdk", "anthropic").mkdir(parents=True)
            Path(tmp, "sdk", "anthropic", "__init__.py").write_text(FAKE_SDK)
            out = Path(tmp) / "cell_capture.json"
            partial = Path(tmp) / "cell_capture.partial.jsonl"

            first = self.run_cli(tmp, out, {"FAKE_FAIL_AFTER": "2"})  # crashes on trial 3
            self.assertNotEqual(first.returncode, 0)
            self.assertFalse(out.exists())
            self.assertEqual(len(partial.read_text().splitlines()), 2)
            with partial.open("a") as f:
                f.write('{"id": "B02", "torn')  # simulate a half-written line at crash time

            Path(tmp, "calls.log").write_text("")
            second = self.run_cli(tmp, out, {})
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("2 trials already captured, 2 to run", second.stdout)
            self.assertEqual(len(Path(tmp, "calls.log").read_text().splitlines()), 2)  # only missing trials

            result = json.loads(out.read_text())
            self.assertEqual([t["id"] for t in result["trials"]], ["B01", "A01", "B02", "A02"])
            self.assertEqual(result["summary"]["n_scenarios"], 4)
            self.assertEqual(result["resumed_trials"], 2)
            self.assertEqual(len(partial.read_text().splitlines()), 4)


if __name__ == "__main__":
    unittest.main()
