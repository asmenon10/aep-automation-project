"""
CLI entry point for Sandbox Diff.
Usage:
    python scripts/run_sandbox_diff.py --sandbox-a prod --sandbox-b dev
    python scripts/run_sandbox_diff.py --sandbox-a prod --sandbox-b dev --export html
    python scripts/run_sandbox_diff.py --sandbox-a prod --sandbox-b dev --export all
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.sandbox_diff import (
    fetch_sandbox_resources,
    compute_diff,
    export_to_csv,
    export_to_html,
    export_to_json,
    print_diff_report,
)

REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare resources across two AEP sandboxes."
    )
    parser.add_argument(
        "--sandbox-a", required=True,
        help="Name of the first sandbox (e.g., prod, dev, stage)",
    )
    parser.add_argument(
        "--sandbox-b", required=True,
        help="Name of the second sandbox to compare against",
    )
    parser.add_argument(
        "--env", default="dev",
        help="Config environment to use for credentials (default: dev)",
    )
    parser.add_argument(
        "--export", choices=["json", "csv", "html", "all"], default=None,
        help="Export the diff report to json, csv, html, or all formats",
    )

    args = parser.parse_args()

    print(f"\n  Fetching resources from [{args.sandbox_a}]...")
    resources_a = fetch_sandbox_resources(args.env, args.sandbox_a)

    print(f"\n  Fetching resources from [{args.sandbox_b}]...")
    resources_b = fetch_sandbox_resources(args.env, args.sandbox_b)

    diff = compute_diff(resources_a, resources_b)
    print_diff_report(diff, args.sandbox_a, args.sandbox_b)

    # Export if requested
    if args.export:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"sandbox_diff_{args.sandbox_a}_vs_{args.sandbox_b}_{timestamp}"

        if args.export in ("json", "all"):
            export_to_json(diff, resources_a, resources_b, args.sandbox_a, args.sandbox_b, REPORTS_DIR / f"{base_name}.json")

        if args.export in ("csv", "all"):
            export_to_csv(diff, resources_a, resources_b, args.sandbox_a, args.sandbox_b, REPORTS_DIR / f"{base_name}.csv")

        if args.export in ("html", "all"):
            export_to_html(diff, resources_a, resources_b, args.sandbox_a, args.sandbox_b, REPORTS_DIR / f"{base_name}.html")


if __name__ == "__main__":
    main()