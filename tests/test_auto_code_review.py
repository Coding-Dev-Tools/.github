"""Execute the shipped YAML run blocks in a separate, caller-like checkout."""

import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github/workflows/auto-code-review.yml",
    ROOT / "templates/workflows/auto-code-review.yml",
)


class InlineWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflows = [
            yaml.safe_load(path.read_text(encoding="utf-8")) for path in WORKFLOWS
        ]
        cls.steps = {
            step.get("id", step["name"]): step
            for step in cls.workflows[0]["jobs"]["review"]["steps"]
        }
        tree = ast.parse(cls.steps["secrets"]["run"])
        cls.exclusions = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                getattr(target, "id", "") == "exclusions" for target in node.targets
            )
        )
        # Capture a real 1.5.0 empty baseline rather than inventing the success schema.
        with tempfile.TemporaryDirectory() as empty:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "detect_secrets",
                    "scan",
                    "--all-files",
                    "--no-verify",
                    "--exclude-files",
                    cls.exclusions,
                ],
                cwd=empty,
                capture_output=True,
                check=True,
            )
        cls.empty = json.loads(completed.stdout)
        assert cls.empty["version"] == "1.5.0"
        assert cls.empty["results"] == {}

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.temp = Path(self.scratch.name)
        self.caller = self.temp / "caller"
        self.caller.mkdir()
        self.runner = self.temp / "runner"
        self.runner.mkdir()
        self.environment = {
            "RUNNER_TEMP": str(self.runner),
            "REVIEW_DIR": str(self.runner / "code-review"),
            "RUFF_CACHE_DIR": str(self.runner / "ruff-cache"),
            "RUFF_TARGETS": ".",
            "SCAN_ENABLED": "true",
            "TODOS_ENABLED": "false",
            "MAX_FILE_SIZE": "0",
        }

    def run_block(
        self,
        step_id,
        *,
        fixture=None,
        missing=False,
        returncode=0,
        version=None,
        env=None,
        process_error=False,
    ):
        """Run exact YAML Python source; stub only the external process boundary."""
        step = self.steps[step_id]
        self.assertEqual(step["shell"], "python")
        output_path = self.runner / "github-output"
        output_path.write_text("", encoding="utf-8")
        environment = (
            self.environment | {"GITHUB_OUTPUT": str(output_path)} | (env or {})
        )
        log = io.StringIO()

        def fake_process(command, **kwargs):
            self.assertEqual(kwargs.get("stderr"), subprocess.DEVNULL)
            if process_error:
                raise OSError("private-value-from-scanner-stderr")
            if "stdout" in kwargs and hasattr(kwargs["stdout"], "write"):
                if missing:
                    target = Path(kwargs["stdout"].name)
                    kwargs["stdout"].close()
                    target.unlink()
                else:
                    raw = (
                        fixture
                        if isinstance(fixture, bytes)
                        else json.dumps(fixture).encode("utf-8")
                    )
                    kwargs["stdout"].write(raw)
            return subprocess.CompletedProcess(command, returncode, stdout=fixture)

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, environment))
            stack.enter_context(contextlib.chdir(self.caller))
            stack.enter_context(contextlib.redirect_stdout(log))
            stack.enter_context(contextlib.redirect_stderr(log))
            if fixture is not None or missing or process_error:
                stack.enter_context(patch("subprocess.run", side_effect=fake_process))
            if version is not None:
                stack.enter_context(
                    patch("importlib.metadata.version", return_value=version)
                )
            try:
                # Executing repository-owned YAML is the purpose of this harness.
                exec(  # noqa: S102
                    compile(step["run"], str(WORKFLOWS[0]) + ":" + step_id, "exec"),
                    {"__name__": "__main__"},
                )
                code = 0
            except SystemExit as exit_result:
                code = exit_result.code
        outputs = dict(
            line.split("=", 1)
            for line in output_path.read_text(encoding="utf-8").splitlines()
        )
        return code, outputs, log.getvalue()

    def successful_steps(self):
        steps = {
            name: {"outcome": "success", "conclusion": "success", "outputs": {}}
            for name in (
                "checkout",
                "python",
                "install-ruff",
                "ruff-lint",
                "ruff-format",
                "install-secrets",
                "secrets",
                "todos",
                "large-files",
            )
        }
        steps["ruff-lint"]["outputs"] = {
            "status": "complete",
            "count": "0",
            "has_issues": "false",
        }
        steps["ruff-format"]["outputs"] = {"status": "complete", "has_issues": "false"}
        steps["secrets"]["outputs"] = {
            "status": "clean",
            "count": "0",
            "has_issues": "false",
        }
        steps["todos"]["outputs"] = {"count": "0", "has_issues": "false"}
        steps["large-files"]["outputs"] = {"has_issues": "false"}
        return steps

    def summary(self, steps, **env):
        code, outputs, log = self.run_block(
            "summary", env={"REVIEW_STEPS": json.dumps(steps)} | env
        )
        self.assertEqual(code, 0)
        body = (Path(self.environment["REVIEW_DIR"]) / "review-summary.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(body, log.strip() + "\n")
        return outputs["overall"], body

    def test_active_and_template_are_identical_and_self_contained(self):
        self.assertEqual(WORKFLOWS[0].read_bytes(), WORKFLOWS[1].read_bytes())
        review = self.workflows[0]["jobs"]["review"]
        self.assertEqual(
            review["env"]["RUFF_CACHE_DIR"], "${{ runner.temp }}/ruff-cache"
        )
        self.assertEqual(self.steps["checkout"]["uses"], "actions/checkout@v4")
        self.assertNotIn("repository", self.steps["checkout"].get("with", {}))
        self.assertIn("detect-secrets==1.5.0", self.steps["install-secrets"]["run"])
        self.assertIn("always()", self.steps["summary"]["if"])
        self.assertIn("always()", self.steps["Check verdict"]["if"])
        for step in self.steps.values():
            if step.get("shell") == "python":
                compile(step["run"], str(WORKFLOWS[0]), "exec")
                self.assertNotIn("${{", step["run"])
                self.assertNotIn("scripts/", step["run"])
        self.assertFalse((self.caller / "scripts").exists())

    def test_valid_empty_scan_passes(self):
        code, outputs, _ = self.run_block("secrets", fixture=self.empty)
        self.assertEqual(
            (code, outputs),
            (0, {"status": "clean", "count": "0", "has_issues": "false"}),
        )
        verdict, _ = self.summary(self.successful_steps())
        self.assertEqual(verdict, "pass")

    def findings(self):
        data = copy.deepcopy(self.empty)
        data["results"] = {
            "src/service.py": [
                {
                    "type": "Secret Keyword",
                    "filename": "src/service.py",
                    "line_number": 3,
                    "hashed_secret": "a" * 40,
                    "is_verified": False,
                }
            ]
        }
        return data

    def test_findings_fail_and_reports_hide_values_hashes_and_stderr(self):
        data = self.findings()
        code, outputs, log = self.run_block("secrets", fixture=data)
        self.assertEqual(
            (code, outputs["status"], outputs["count"]), (1, "findings", "1")
        )
        steps = self.successful_steps()
        steps["secrets"] = {
            "outcome": "failure",
            "conclusion": "success",
            "outputs": outputs,
        }
        verdict, body = self.summary(steps)
        self.assertEqual(verdict, "fail")
        self.assertNotIn(
            data["results"]["src/service.py"][0]["hashed_secret"], log + body
        )
        self.assertNotIn("src/service.py", log + body)

    def test_nonzero_scan_fails_even_with_valid_empty_json(self):
        code, outputs, log = self.run_block("secrets", fixture=self.empty, returncode=2)
        self.assertEqual((code, outputs), (1, {"status": "error"}))
        self.assertNotIn("Traceback", log)

    def test_launch_errors_and_unexpected_secret_values_are_sanitized(self):
        code, outputs, log = self.run_block("secrets", process_error=True)
        self.assertEqual((code, outputs), (1, {"status": "error"}))
        self.assertNotIn("private-value-from-scanner-stderr", log)
        data = self.findings()
        data["results"]["src/service.py"][0]["secret_value"] = "private-scanner-value"
        code, outputs, log = self.run_block("secrets", fixture=data)
        self.assertEqual((code, outputs), (1, {"status": "error"}))
        self.assertNotIn("private-scanner-value", log)

    def test_missing_and_malformed_json_fail(self):
        for raw in (
            b"",
            b"{",
            b"scanner-private-value",
            b"[]",
            b"null",
            b'{"results": {}}',
            b'{"version":"1.5.0","version":"1.5.0"}',
            b'{"x":NaN}',
        ):
            with self.subTest(raw=raw):
                code, outputs, log = self.run_block("secrets", fixture=raw)
                self.assertEqual((code, outputs), (1, {"status": "error"}))
                self.assertNotIn("scanner-private-value", log)
        code, outputs, _ = self.run_block("secrets", missing=True)
        self.assertEqual((code, outputs), (1, {"status": "error"}))

    def test_invalid_version_plugins_filters_and_schema_fail(self):
        mutations = [
            ("version", "1.4.0"),
            ("version", None),
            ("plugins_used", []),
            ("plugins_used", {}),
            ("plugins_used", [{"name": "UnknownPlugin"}]),
            ("plugins_used", self.empty["plugins_used"][:-1]),
            ("filters_used", []),
            ("filters_used", None),
            ("results", []),
            ("results", None),
            ("generated_at", "yesterday"),
            ("generated_at", None),
        ]
        wrong_limit = copy.deepcopy(self.empty["plugins_used"])
        next(plugin for plugin in wrong_limit if "limit" in plugin)["limit"] = 100
        mutations.append(("plugins_used", wrong_limit))
        for key, value in mutations:
            with self.subTest(field=key, value=value):
                data = copy.deepcopy(self.empty)
                data[key] = value
                code, outputs, _ = self.run_block("secrets", fixture=data)
                self.assertEqual((code, outputs), (1, {"status": "error"}))
        for key in self.empty:
            with self.subTest(missing=key):
                data = copy.deepcopy(self.empty)
                del data[key]
                self.assertEqual(
                    self.run_block("secrets", fixture=data)[:2],
                    (1, {"status": "error"}),
                )
        self.assertEqual(
            self.run_block("secrets", fixture=self.empty, version="1.4.0")[:2],
            (1, {"status": "error"}),
        )

    def test_invalid_finding_records_fail(self):
        for key, value in [
            ("line_number", 0),
            ("line_number", True),
            ("line_number", "3"),
            ("type", "Unknown type"),
            ("filename", "different.py"),
            ("hashed_secret", "private-value"),
            ("is_verified", "false"),
        ]:
            with self.subTest(field=key, value=value):
                data = self.findings()
                data["results"]["src/service.py"][0][key] = value
                self.assertEqual(
                    self.run_block("secrets", fixture=data)[:2],
                    (1, {"status": "error"}),
                )
        for findings in (None, {}, [None], ["private-value"]):
            data = copy.deepcopy(self.empty)
            data["results"] = {"source.py": findings}
            self.assertEqual(
                self.run_block("secrets", fixture=data)[:2], (1, {"status": "error"})
            )

    def test_required_failed_skipped_and_missing_steps_fail(self):
        for name in self.successful_steps():
            for outcome in ("failure", "error", "skipped", "cancelled", ""):
                with self.subTest(step=name, outcome=outcome):
                    steps = self.successful_steps()
                    steps[name]["outcome"] = outcome
                    # conclusion can say success after continue-on-error; inspect outcome.
                    steps[name]["conclusion"] = "success"
                    self.assertEqual(
                        self.summary(steps, TODOS_ENABLED="true", MAX_FILE_SIZE="500")[
                            0
                        ],
                        "fail",
                    )
            steps = self.successful_steps()
            del steps[name]
            self.assertEqual(
                self.summary(steps, TODOS_ENABLED="true", MAX_FILE_SIZE="500")[0],
                "fail",
            )

    def test_missing_inconsistent_and_error_outputs_fail(self):
        for name in ("ruff-lint", "ruff-format", "secrets", "todos", "large-files"):
            for key in self.successful_steps()[name]["outputs"]:
                with self.subTest(step=name, missing=key):
                    steps = self.successful_steps()
                    del steps[name]["outputs"][key]
                    self.assertEqual(
                        self.summary(steps, TODOS_ENABLED="true", MAX_FILE_SIZE="500")[
                            0
                        ],
                        "fail",
                    )
        for count in ("", "-1", "nan", "00", "1.0"):
            steps = self.successful_steps()
            steps["secrets"]["outputs"]["count"] = count
            self.assertEqual(self.summary(steps)[0], "fail")
        for status in ("error", "findings", ""):
            steps = self.successful_steps()
            steps["secrets"]["outputs"]["status"] = status
            self.assertEqual(self.summary(steps)[0], "fail")
        steps = self.successful_steps()
        steps["secrets"]["outputs"]["count"] = "1"
        self.assertEqual(self.summary(steps)[0], "fail")

    def test_explicit_disabled_optional_checks_pass_without_claiming_scan_coverage(
        self,
    ):
        steps = self.successful_steps()
        for name in ("install-secrets", "secrets", "todos", "large-files"):
            steps[name] = {"outcome": "skipped", "outputs": {}}
        verdict, body = self.summary(steps, SCAN_ENABLED="false")
        self.assertEqual(verdict, "pass")
        self.assertIn("Disabled by caller", body)
        self.assertNotIn("Secret detection: 0", body)

    def test_valid_lint_and_format_findings_remain_warnings(self):
        for name in ("ruff-lint", "ruff-format", "todos", "large-files"):
            with self.subTest(step=name):
                steps = self.successful_steps()
                steps[name]["outputs"]["has_issues"] = "true"
                if "count" in steps[name]["outputs"]:
                    steps[name]["outputs"]["count"] = "1"
                self.assertEqual(
                    self.summary(steps, TODOS_ENABLED="true", MAX_FILE_SIZE="500")[0],
                    "warn",
                )

    def test_final_verdict_fails_closed(self):
        for outcome in ("failure", "skipped", "cancelled", ""):
            self.assertEqual(
                self.run_block(
                    "Check verdict", env={"SUMMARY_OUTCOME": outcome, "VERDICT": "pass"}
                )[0],
                1,
            )
        for verdict in ("fail", "", "clean", "unexpected"):
            self.assertEqual(
                self.run_block(
                    "Check verdict",
                    env={"SUMMARY_OUTCOME": "success", "VERDICT": verdict},
                )[0],
                1,
            )
        for verdict in ("pass", "warn"):
            self.assertEqual(
                self.run_block(
                    "Check verdict",
                    env={"SUMMARY_OUTCOME": "success", "VERDICT": verdict},
                )[0],
                0,
            )

    def test_real_scan_empty_and_synthetic_source_and_test_findings(self):
        self.assertEqual(
            self.run_block("secrets")[:2],
            (0, {"status": "clean", "count": "0", "has_issues": "false"}),
        )
        # Construct an offline-only private-key marker at runtime: no fixture allowlist or real credential.
        marker = "-----BEGIN RSA " + "PRIVATE KEY-----"
        for location in ("src/fixture.py", "tests/fixture.py"):
            with self.subTest(location=location):
                target = self.caller / location
                target.parent.mkdir(exist_ok=True)
                target.write_text(marker + "\n", encoding="utf-8")
                code, outputs, log = self.run_block("secrets")
                self.assertEqual((code, outputs["status"]), (1, "findings"))
                self.assertGreater(int(outputs["count"]), 0)
                self.assertNotIn(marker, log)
                target.unlink()
        # Baseline files are not globally hidden by the workflow's exclusions.
        (self.caller / ".secrets.baseline").write_text(marker + "\n", encoding="utf-8")
        self.assertEqual(self.run_block("secrets")[1]["status"], "findings")

    def test_offline_scan_keeps_all_detectors_without_verification_or_network(self):
        from detect_secrets.settings import default_settings

        with default_settings() as settings:
            expected_plugins = settings.json()["plugins_used"]
        self.assertEqual(self.empty["plugins_used"], expected_plugins)
        self.assertEqual(len(expected_plugins), 27)
        self.assertNotIn(
            "detect_secrets.filters.common.is_ignored_due_to_verification_policies",
            [item["path"] for item in self.empty["filters_used"]],
        )
        token = "ghp_" + hashlib.sha256(b"offline GitHub fixture").hexdigest()[:36]
        aws_id = (
            "AKIA" + hashlib.sha256(b"offline AWS fixture").hexdigest()[:16].upper()
        )
        (self.caller / "source.py").write_text(
            f'github_token = "{token}"\naws_id = "{aws_id}"\n', encoding="utf-8"
        )
        audit = self.runner / "offline-audit.json"
        # Execute the real CLI with every plugin verifier and network entry blocked.
        # One core keeps all audit counters in this process on Windows and Linux.
        guard = """
import contextlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
from detect_secrets.main import main
from detect_secrets.settings import default_settings, get_plugins

calls = {'verification': 0, 'network': 0}
def verifier(*args, **kwargs):
    calls['verification'] += 1
    raise AssertionError('Verification is forbidden')
def network(*args, **kwargs):
    calls['network'] += 1
    raise AssertionError('Network is forbidden')
with default_settings():
    classes = [type(plugin) for plugin in get_plugins()]
try:
    with contextlib.ExitStack() as stack:
        for plugin in classes:
            stack.enter_context(patch.object(plugin, 'verify', verifier))
        for entry in ('requests.sessions.Session.request', 'socket.socket.connect',
                      'socket.socket.connect_ex', 'socket.socket.sendto',
                      'socket.create_connection', 'socket.getaddrinfo'):
            stack.enter_context(patch(entry, network))
        result = main(['--cores', '1', *sys.argv[2:]])
finally:
    Path(sys.argv[1]).write_text(json.dumps(calls), encoding='utf-8')
raise SystemExit(99 if any(calls.values()) else result)
"""
        real_run = subprocess.run
        baselines = []
        process_codes = []

        def guarded_process(command, **kwargs):
            self.assertEqual(
                command[:4], [sys.executable, "-I", "-m", "detect_secrets"]
            )
            self.assertIn("--no-verify", command)
            self.assertFalse(any(arg.startswith("--disable-") for arg in command))
            completed = real_run(
                [sys.executable, "-I", "-c", guard, str(audit), *command[4:]], **kwargs
            )
            process_codes.append(completed.returncode)
            if completed.returncode == 0:
                baselines.append(json.loads(Path(kwargs["stdout"].name).read_bytes()))
            return completed

        with patch("subprocess.run", side_effect=guarded_process):
            code, outputs, log = self.run_block("secrets")
        self.assertEqual(process_codes, [0])
        self.assertEqual((code, outputs["status"]), (1, "findings"))
        self.assertEqual(
            json.loads(audit.read_text()), {"verification": 0, "network": 0}
        )
        self.assertEqual(baselines[0]["plugins_used"], expected_plugins)
        findings = [
            item for values in baselines[0]["results"].values() for item in values
        ]
        self.assertTrue(
            {"GitHub Token", "AWS Access Key"}.issubset(
                {item["type"] for item in findings}
            )
        )
        self.assertTrue(all(item["is_verified"] is False for item in findings))
        self.assertNotIn(token, log)
        self.assertNotIn(aws_id, log)

    def test_output_with_network_verification_filter_is_rejected(self):
        data = copy.deepcopy(self.empty)
        data["filters_used"].append(
            {
                "path": "detect_secrets.filters.common.is_ignored_due_to_verification_policies",
                "min_level": 2,
            }
        )
        data["filters_used"].sort(key=lambda item: item["path"].lower())
        self.assertEqual(
            self.run_block("secrets", fixture=data)[:2], (1, {"status": "error"})
        )

    def test_caller_module_cannot_shadow_the_installed_scanner(self):
        shadow = self.caller / "detect_secrets"
        shadow.mkdir()
        (shadow / "__init__.py").write_text("", encoding="utf-8")
        (shadow / "__main__.py").write_text("raise SystemExit(42)\n", encoding="utf-8")
        self.assertEqual(self.run_block("secrets")[1]["status"], "clean")

    def test_real_ruff_warnings_and_cache_stay_outside_checkout(self):
        (self.caller / "pyproject.toml").write_text(
            '[tool.ruff]\ncache-dir = ".ruff_cache"\n', encoding="utf-8"
        )
        (self.caller / "source.py").write_text(
            "import os\nvalue=  1\n", encoding="utf-8"
        )
        steps = self.successful_steps()
        for name in ("ruff-lint", "ruff-format"):
            code, outputs, _ = self.run_block(name)
            self.assertEqual(code, 0)
            self.assertEqual(outputs["has_issues"], "true")
            steps[name]["outputs"] = outputs
        self.assertEqual(self.summary(steps)[0], "warn")
        self.assertTrue((self.runner / "ruff-cache").is_dir())
        self.assertFalse((self.caller / ".ruff_cache").exists())

    def test_ruff_process_errors_do_not_become_clean_or_warnings(self):
        (self.caller / "pyproject.toml").write_text("[tool.ruff\n", encoding="utf-8")
        for name in ("ruff-lint", "ruff-format"):
            code, outputs, _ = self.run_block(name)
            self.assertEqual((code, outputs), (1, {"status": "error"}))

    def test_optional_checks_retain_warnings_and_do_not_hide_process_errors(self):
        code, outputs, _ = self.run_block("todos", fixture=b"source.py\x00")
        self.assertEqual((code, outputs), (0, {"count": "0", "has_issues": "false"}))
        (self.caller / "source.py").write_text(
            "# TODO: review this\n", encoding="utf-8"
        )
        code, outputs, _ = self.run_block("todos", fixture=b"source.py\x00")
        self.assertEqual((code, outputs), (0, {"count": "1", "has_issues": "true"}))
        (self.caller / "large.bin").write_bytes(b"x" * 1025)
        self.assertEqual(
            self.run_block("large-files", env={"MAX_FILE_SIZE": "1"})[:2],
            (0, {"has_issues": "true"}),
        )
        # A real failing git diff must fail the step, not produce zero TODOs.
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_block("todos", env={"BASE_SHA": "missing", "HEAD_SHA": "missing"})

    def test_oversized_check_ignores_symlinks_and_still_checks_regular_files(self):
        # Model a dangling link on platforms where creating symlinks is restricted.
        target = self.caller / "dangling-link"
        target.write_bytes(b"x" * 2048)
        original = Path.is_symlink
        with patch.object(
            Path,
            "is_symlink",
            lambda path: path.name == "dangling-link" or original(path),
        ):
            self.assertEqual(
                self.run_block("large-files", env={"MAX_FILE_SIZE": "1"})[:2],
                (0, {"has_issues": "false"}),
            )
            (self.caller / "regular.bin").write_bytes(b"x" * 1025)
            self.assertEqual(
                self.run_block("large-files", env={"MAX_FILE_SIZE": "1"})[:2],
                (0, {"has_issues": "true"}),
            )

    @unittest.skipIf(
        os.name == "nt", "Native symlink fixture is exercised by Ubuntu CI"
    )
    def test_real_dangling_symlink_does_not_fail_oversized_check(self):
        (self.caller / "dangling-link").symlink_to("missing-target")
        self.assertEqual(
            self.run_block("large-files", env={"MAX_FILE_SIZE": "1"})[:2],
            (0, {"has_issues": "false"}),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
