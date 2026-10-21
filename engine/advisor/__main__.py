import argparse
import dataclasses
import json
from pathlib import Path

from engine.advisor.service import discover_specialists, discover_workflows, get_general_guidance


def main():
    parser = argparse.ArgumentParser(description="Advisor Read-Only Diagnostic Utility")
    parser.add_argument("--repo-root", default=".", help="Path to repo root")
    parser.add_argument("--project", help="Project key to inspect")
    parser.add_argument("--list-specialists", action="store_true", help="List specialists")
    parser.add_argument("--list-workflows", action="store_true", help="List workflows")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.list_specialists:
        specs = discover_specialists(repo_root)
        print(json.dumps(specs, indent=2))
        return

    if args.list_workflows:
        wfs = discover_workflows(repo_root)
        print(json.dumps(wfs, indent=2))
        return

    guidance = get_general_guidance(repo_root, args.project)
    print(json.dumps(dataclasses.asdict(guidance), indent=2))


if __name__ == "__main__":
    main()
