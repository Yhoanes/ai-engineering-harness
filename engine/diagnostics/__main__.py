import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from engine.diagnostics.engine import run_diagnostics


def _print_human(report):
    print("AI Engineering Harness")
    print(f"Version: {report.harness_version or 'UNKNOWN'}")
    print()

    for check in report.checks:
        id_str = check.id.replace("_", " ").title()
        # pad to 24 chars with dots
        padded = f"{id_str} ".ljust(24, ".")
        print(f"{padded} {check.status}")

    print(f"\nSTATUS: {report.overall_status}")


def _get_exit_code(status: str) -> int:
    codes = {
        "READY": 0,
        "INSTALLATION_ERROR": 1,
        "REQUIREMENT_MISSING": 2,
        "CONFIGURATION_ERROR": 3,
    }
    return codes.get(status, 3)


def main():
    parser = argparse.ArgumentParser(description="AI Engineering Harness Diagnostics")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--repo-root", type=str, default=".", help="Root directory of the repository"
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report = run_diagnostics(repo_root)

    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        _print_human(report)

    sys.exit(_get_exit_code(report.overall_status))


if __name__ == "__main__":
    main()
