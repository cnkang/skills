#!/usr/bin/env python3
"""Reject empty/skipped/failed acceptance suites from a pytest JUnit report."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def validate_report(path: Path, minimum: int) -> None:
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if len(cases) < minimum:
        raise ValueError(f"Expected at least {minimum} test cases, got {len(cases)}")
    rejected = [case.get("name") for case in cases
                if any(case.find(tag) is not None for tag in ("skipped", "failure", "error"))]
    if rejected:
        raise ValueError(f"Acceptance cases did not pass: {rejected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--minimum-tests", type=int, default=1)
    args = parser.parse_args()
    if args.minimum_tests < 1:
        parser.error("--minimum-tests must be positive")
    validate_report(args.report, args.minimum_tests)
    print("Acceptance report passed with no skips/failures/errors")


if __name__ == "__main__":
    main()
