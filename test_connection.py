"""Quick smoke test — verify which sandbox you're actually connected to."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.connection import connect


def main() -> None:
    try:
        connect("dev")

        from aepp import schema
        s = schema.Schema()
        raw = s.getSchemas()

        latest_five = raw[:5] if isinstance(raw, list) else []

        print(f"\n  Latest 5 schemas in this sandbox:")
        print(f"  {'='*50}")

        for item in latest_five:
            if isinstance(item, dict):
                title = item.get("title", "untitled")
                schema_id = item.get("$id", "no id")
                print(f"    - {title}")
                print(f"      ID: {schema_id}")
            else:
                print(f"    - {item}")

        if not latest_five:
            print("    No schemas found.")

    except Exception as exc:
        print(f"\n  🔴 Failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()