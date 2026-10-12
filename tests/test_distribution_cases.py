"""Keep selection growth bounded without dropping original coverage."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from test_distribution import selection_cases
from validate_skills import LEGACY_SKILLS, QDRANT_SKILLS, SKILLS


def test_selection_coverage():
    cases = selection_cases()
    assert len(cases) == len(set(cases))
    assert len(cases) == 15 + 2 + len(LEGACY_SKILLS)
    assert all((name,) in cases for name in SKILLS)
    assert QDRANT_SKILLS in cases and SKILLS in cases
    for size in range(1, len(LEGACY_SKILLS) + 1):
        assert all(case in cases for case in itertools.combinations(LEGACY_SKILLS, size))
