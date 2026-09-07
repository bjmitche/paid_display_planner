#!/usr/bin/env python3
"""Verify that the Notion data model is readable and complete for the app."""
from __future__ import annotations

import json
import sys

from planner.notion_client import client_from_environment


def main() -> int:
    results = client_from_environment().verify()
    payload = {
        "status": "ok" if all(result.ok for result in results) else "error",
        "data_sources": [
            {
                "key": result.key,
                "data_source_id": result.data_source_id,
                "title": result.title,
                "row_count": result.row_count,
                "property_count": result.property_count,
                "missing_properties": list(result.missing_properties),
                "type_mismatches": list(result.type_mismatches),
                "ok": result.ok,
            }
            for result in results
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
