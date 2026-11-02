"""Direct checks for the helpers extracted during the maintainability split."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative_path: str, module_name: str):
    """Import one script module by path without installing it."""
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def commit_validator():
    return load(
        "conventional-commit-batcher/scripts/validate_conventional_commit.py",
        "extracted_commit_validator",
    )


@pytest.fixture(scope="module")
def quality_probe():
    return load(
        "repository-quality-gate-fixer/scripts/repo_quality_probe.py",
        "extracted_quality_probe",
    )


@pytest.fixture(scope="module")
def workbuddy_release():
    return load("integrations/workbuddy/release.py", "extracted_workbuddy_release")


def test_footer_lines_are_recognised(commit_validator):
    """Breaking-change and generic footers are both footer lines."""
    assert commit_validator.is_footer_line("BREAKING CHANGE: remove the old flag")
    assert commit_validator.is_footer_line("Refs: #12")
    assert not commit_validator.is_footer_line("a plain body line")


def test_footer_section_accepts_continuations_only(commit_validator):
    """A footer section allows blank lines, footers and indented continuations."""
    assert commit_validator.is_valid_footer_section(["Refs: #12", "", " continued detail"])
    assert not commit_validator.is_valid_footer_section(["Refs: #12", "unindented prose"])


def test_first_alpha_char_skips_leading_symbols(commit_validator):
    """Style checks read the first letter, not a leading punctuation mark."""
    assert commit_validator.first_alpha_char("  (add) feature") == "a"
    assert commit_validator.first_alpha_char("1234") is None


def test_safe_git_argument_accepts_known_options_only(quality_probe):
    """Only allow-listed options and plain identifiers may reach git."""
    assert quality_probe.is_safe_git_arg("HEAD~1")
    assert quality_probe.is_safe_git_arg("--cached")
    assert not quality_probe.is_safe_git_arg("--upload-pack=evil")
    assert not quality_probe.is_safe_git_arg("a;rm -rf /")


def test_root_depth_reports_entries_outside_the_root(quality_probe):
    """A walked directory outside the root has no depth and is skipped."""
    root = Path("/tmp/probe-root")
    assert quality_probe._root_depth(root, root) == 0
    assert quality_probe._root_depth(root / "child", root) == 1
    assert quality_probe._root_depth(Path("/tmp/other"), root) is None


def test_checked_git_argument_refuses_flags_outside_the_allow_list(workbuddy_release):
    """Release helpers refuse option-like arguments and shell metacharacters."""
    assert workbuddy_release.checked_git_arg("v1.2.3") == "v1.2.3"
    assert workbuddy_release.checked_git_arg("--porcelain") == "--porcelain"
    with pytest.raises(ValueError):
        workbuddy_release.checked_git_arg("--upload-pack=evil")
    with pytest.raises(ValueError):
        workbuddy_release.checked_git_arg("a b")
