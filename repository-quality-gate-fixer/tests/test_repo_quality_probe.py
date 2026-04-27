from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPT_DIR / "repo_quality_probe.py"

sys_path_inserted = False


def _ensure_importable():
    global sys_path_inserted
    if not sys_path_inserted:
        sys.path.insert(0, str(SCRIPT_DIR))
        sys_path_inserted = True


_ensure_importable()

from repo_quality_probe import (
    BLOCK_SCALARS,
    RUN_STEP_RE,
    _is_block_scalar,
    _is_folded_block_scalar,
    _strip_yaml_comment,
    collect,
    discover_agent_files,
    display_path,
    extract_workflow_steps,
    redact_text,
)


def run_probe(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(cwd) if cwd else None,
    )


class TestStripYamlComment(unittest.TestCase):
    def test_no_comment(self):
        self.assertEqual(_strip_yaml_comment("npm ci"), "npm ci")

    def test_trailing_comment(self):
        self.assertEqual(_strip_yaml_comment("| # shell block"), "|")

    def test_comment_with_spaces(self):
        self.assertEqual(_strip_yaml_comment(">- # fold"), ">-")

    def test_no_strip_in_value(self):
        self.assertEqual(_strip_yaml_comment("echo '# not a comment'"), "echo '# not a comment'")


class TestRunStepRegex(unittest.TestCase):
    def test_matches_dash_run(self):
        m = RUN_STEP_RE.match("      - run: npm ci")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("value").strip(), "npm ci")

    def test_matches_run_without_dash(self):
        m = RUN_STEP_RE.match("    run: npm ci")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("value").strip(), "npm ci")

    def test_matches_run_block_literal(self):
        m = RUN_STEP_RE.match("      - run: |")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("value").strip(), "|")

    def test_matches_run_block_folded(self):
        m = RUN_STEP_RE.match("      - run: >")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("value").strip(), ">")

    def test_matches_run_chomp_variants(self):
        for variant in ("|-", ">-", "|+", ">+"):
            with self.subTest(variant=variant):
                m = RUN_STEP_RE.match(f"      - run: {variant}")
                self.assertIsNotNone(m)
                self.assertEqual(m.group("value").strip(), variant)


class TestBlockScalarFunction(unittest.TestCase):
    def test_basic_scalars(self):
        for v in ("|", ">", "|-", ">-", "|+", ">+"):
            with self.subTest(v=v):
                self.assertTrue(_is_block_scalar(v))

    def test_indent_indicators(self):
        for v in ("|2", ">2", "|4", ">4"):
            with self.subTest(v=v):
                self.assertTrue(_is_block_scalar(v))

    def test_chomp_with_indent(self):
        for v in ("|-2", ">-2", "|+2", ">+2", "|2+", ">2-"):
            with self.subTest(v=v):
                self.assertTrue(_is_block_scalar(v))

    def test_not_block_scalar(self):
        for v in ("npm ci", "echo hello", "", "run:"):
            with self.subTest(v=v):
                self.assertFalse(_is_block_scalar(v))

    def test_folded_detection(self):
        self.assertTrue(_is_folded_block_scalar(">"))
        self.assertTrue(_is_folded_block_scalar(">-"))
        self.assertTrue(_is_folded_block_scalar(">2"))
        self.assertFalse(_is_folded_block_scalar("|"))
        self.assertFalse(_is_folded_block_scalar("|-"))

    def test_block_scalars_set_is_subset(self):
        for v in BLOCK_SCALARS:
            with self.subTest(v=v):
                self.assertTrue(_is_block_scalar(v))


class TestExtractWorkflowSteps(unittest.TestCase):
    def _write_workflow(self, repo: Path, content: str) -> Path:
        workflow_dir = repo / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow = workflow_dir / "ci.yml"
        workflow.write_text(content, encoding="utf-8")
        return workflow

    def _extract(self, repo: Path) -> list[str]:
        steps = extract_workflow_steps(repo, [".github/workflows/ci.yml"])
        return steps[".github/workflows/ci.yml"]

    def test_extracts_dash_run_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm ci\n",
            )
            self.assertIn("npm ci", self._extract(repo))

    def test_extracts_dash_run_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                'name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: "npm run lint"\n      - run: \'npm test\'\n',
            )
            extracted = self._extract(repo)
            self.assertIn("npm run lint", extracted)
            self.assertIn("npm test", extracted)

    def test_extracts_block_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          npm run lint\n          npm test\n",
            )
            extracted = self._extract(repo)
            joined = "\n".join(extracted)
            self.assertIn("npm run lint", joined)
            self.assertIn("npm test", joined)

    def test_extracts_block_folded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: >\n          echo hello\n          echo world\n",
            )
            extracted = self._extract(repo)
            self.assertTrue(len(extracted) > 0)
            self.assertIn("echo hello", extracted[0])
            self.assertIn("echo world", extracted[0])

    def test_mixed_run_styles(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm ci\n      - run: |\n          npm run lint\n          npm test\n      - run: >\n          echo hello\n          echo world\n",
            )
            extracted = self._extract(repo)
            self.assertIn("npm ci", extracted)
            self.assertTrue(any("npm run lint" in s for s in extracted))
            self.assertTrue(any("npm test" in s for s in extracted))
            self.assertTrue(any("echo hello" in s for s in extracted))

    def test_no_run_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n",
            )
            self.assertEqual(self._extract(repo), [])

    def test_unreadable_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(repo, "name: CI\n")
            original_read_text = Path.read_text

            def _mock_read_text(self_path, *args, **kwargs):
                if str(self_path).endswith("ci.yml"):
                    raise OSError("permission denied")
                return original_read_text(self_path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", _mock_read_text):
                steps = extract_workflow_steps(repo, [".github/workflows/ci.yml"])
            extracted = steps[".github/workflows/ci.yml"]
            self.assertTrue(any("unable to read" in s for s in extracted))

    def test_ignores_run_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: # intentionally omitted\n      - run: npm ci\n",
            )
            extracted = self._extract(repo)
            self.assertNotIn("# intentionally omitted", extracted)
            self.assertIn("npm ci", extracted)

    def test_block_scalar_with_indent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |2\n          npm run lint\n          npm test\n",
            )
            extracted = self._extract(repo)
            joined = "\n".join(extracted)
            self.assertIn("npm run lint", joined)

    def test_ignores_env_run_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - name: env case\n        env:\n          run: not-a-step\n      - run: echo real\n",
            )
            extracted = self._extract(repo)
            self.assertNotIn("not-a-step", extracted)
            self.assertIn("echo real", extracted)

    def test_ignores_with_run_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: example/action@v1\n        with:\n          run: not-a-step\n      - run: echo real\n",
            )
            extracted = self._extract(repo)
            self.assertNotIn("not-a-step", extracted)
            self.assertIn("echo real", extracted)

    def test_block_scalar_with_inline_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: | # shell block\n          echo hi\n",
            )
            extracted = self._extract(repo)
            self.assertNotIn("| # shell block", extracted)
            self.assertTrue(any("echo hi" in s for s in extracted))

    def test_folded_block_scalar_with_inline_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_workflow(
                repo,
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: >- # fold\n          echo hello\n          echo world\n",
            )
            extracted = self._extract(repo)
            self.assertNotIn(">- # fold", extracted)
            self.assertTrue(any("echo hello" in s for s in extracted))


class TestNonGitRepo(unittest.TestCase):
    def test_probe_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = run_probe(str(repo), "--no-skill-scan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Repository Quality Probe", result.stdout)


class TestSecretRedaction(unittest.TestCase):
    def test_redacts_url_credentials(self):
        text = "https://user:secret@github.com/org/repo.git"
        redacted = redact_text(text)
        self.assertNotIn("secret", redacted)
        self.assertIn("<redacted>", redacted)

    def test_redacts_github_token(self):
        text = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        redacted = redact_text(text)
        self.assertNotIn("ghp_", redacted)

    def test_redacts_github_pat(self):
        text = "github_pat_11ABCDEFGHIJKLMNOPQRST"
        redacted = redact_text(text)
        self.assertNotIn("github_pat_", redacted)

    def test_redacts_token_assignment(self):
        text = "SONAR_TOKEN=mysecretvalue"
        redacted = redact_text(text)
        self.assertNotIn("mysecretvalue", redacted)

    def test_redacts_colon_form(self):
        text = "SONAR_TOKEN: mysecretvalue"
        redacted = redact_text(text)
        self.assertNotIn("mysecretvalue", redacted)

    def test_redacts_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9payload"
        redacted = redact_text(text)
        self.assertNotIn("eyJhbGci", redacted)

    def test_redacts_basic_auth(self):
        text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
        redacted = redact_text(text)
        self.assertNotIn("dXNlcjpwYXNz", redacted)

    def test_redacts_private_key_block(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"
        redacted = redact_text(text)
        self.assertNotIn("MIIEpAIB", redacted)
        self.assertIn("<redacted-private-key>", redacted)

    def test_redacts_sonar_login(self):
        text = "sonar.login=mysecretvalue"
        redacted = redact_text(text)
        self.assertNotIn("mysecretvalue", redacted)

    def test_redacts_json_token_key(self):
        text = '{"token": "mysecretvalue"}'
        redacted = redact_text(text)
        self.assertNotIn("mysecretvalue", redacted)


class TestDisplayPath(unittest.TestCase):
    def test_home_replacement(self):
        home = str(Path.home())
        self.assertEqual(display_path(home), "~")
        self.assertEqual(display_path(home + "/projects/foo"), "~/projects/foo")

    def test_non_home_path_unchanged(self):
        self.assertEqual(display_path("/tmp/foo"), "/tmp/foo")


class TestDiscoverAgentFiles(unittest.TestCase):
    def test_finds_root_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            found = discover_agent_files(repo)
            self.assertIn("AGENTS.md", found)

    def test_finds_nested_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sub = repo / "src" / "foo"
            sub.mkdir(parents=True)
            (sub / "AGENTS.md").write_text("# Foo Agents\n", encoding="utf-8")
            found = discover_agent_files(repo)
            self.assertIn(os.path.join("src", "foo", "AGENTS.md"), found)

    def test_respects_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            deep = repo / "a" / "b" / "c" / "d" / "e" / "f"
            deep.mkdir(parents=True)
            (deep / "AGENTS.md").write_text("# Deep\n", encoding="utf-8")
            found = discover_agent_files(repo, max_depth=3)
            self.assertEqual(found, [])


class TestSkillLimit(unittest.TestCase):
    def test_skill_limit_zero_disables_scan(self):
        result = run_probe(
            ".", "--skill-limit", "0", "--no-skill-scan",
            cwd=Path(__file__).resolve().parent.parent,
        )
        self.assertEqual(result.returncode, 0)


class TestJsonOutput(unittest.TestCase):
    def test_json_contains_schema_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = run_probe(str(repo), "--no-skill-scan", "--json")
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertIn("schema_version", data)
            self.assertIn("probe_version", data)
            self.assertIn("generated_at", data)


class TestDiffScope(unittest.TestCase):
    def test_non_git_repo_diff_scope_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            data = collect(repo, skill_limit=0, skill_scan=False)
            self.assertEqual(data["diff_scope"], {})
            self.assertIn("Not a git repository", " ".join(data["warnings"]))

    def test_invalid_base_ref_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "init"],
                cwd=repo, check=True, capture_output=True,
            )
            data = collect(repo, skill_limit=0, skill_scan=False, base_ref="does-not-exist")
            self.assertEqual(data["diff_scope"]["base_ref_source"], "explicit_unresolved")


if __name__ == "__main__":
    unittest.main()
