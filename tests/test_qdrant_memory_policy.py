"""Keep the memory-judgment guidance routed, honest about the tool surface, and free of local data."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "qdrant-memory"
REFERENCES = ("memory-policy.md", "search-policy.md", "experience-capture.md")
CATEGORIES = ("preference", "fact", "project", "experience", "procedure", "decision")


def text(name):
    """Read one packaged reference without importing the runtime."""
    return (SKILL / "references" / name).read_text(encoding="utf-8")


def test_entrypoint_routes_each_policy_reference():
    """Every policy reference must be packaged and reachable from the entrypoint."""
    entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for name in REFERENCES:
        assert (SKILL / "references" / name).is_file()
        assert f"(references/{name})" in entry


def test_taxonomy_categories_are_documented():
    """The recommended vocabulary must stay visible and complete."""
    policy = text("memory-policy.md")
    for category in CATEGORIES:
        assert f"`{category}`" in policy


def test_add_and_update_document_no_category_argument():
    """The guidance must not invent a category argument for writes."""
    rows = [
        line
        for line in text("tools.md").splitlines()
        if line.startswith("| `qdrant_memory_add`") or line.startswith("| `qdrant_memory_update`")
    ]
    assert len(rows) == 2
    assert all("category" not in row for row in rows)
    policy = " ".join(text("memory-policy.md").split())
    assert "They have no category argument" in policy


def test_search_policy_keeps_both_decision_lists():
    """Both the positive and the negative search triggers must remain documented."""
    policy = text("search-policy.md")
    for heading in ("## Consider a search", "## Do not search by default", "## Query construction"):
        assert heading in policy


def test_task_learning_is_not_described_as_shipped():
    """An unimplemented automatic policy must stay labelled as an assessment."""
    capture = text("experience-capture.md")
    assert "## Automatic task learning" in capture
    assert "not part of the shipped Runtime" in capture


def test_package_has_no_local_paths_or_review_markers():
    """Packaged text must stay portable and free of local or review-only markers."""
    pattern = re.compile(r"/Users/|/Volumes/|\bcodex/|REVIEW_|\bacpx\b")
    for path in SKILL.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py"}:
            assert not pattern.search(path.read_text(encoding="utf-8")), path
