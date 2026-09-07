#!/usr/bin/env python3
"""Idempotently add the Paid Display Planner fields to existing Notion data sources."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
DATA_SOURCES = {
    "inventory": "2d95575d-d8f1-807e-bd84-000bf7007053",
    "activations": "2dd5575d-d8f1-805c-a94f-000b33d68795",
    "products": "2fd5575d-d8f1-800a-b94e-000bb2b0eade",
}

MODEL: dict[str, dict[str, Any]] = {
    "inventory": {
        "Format": {
            "select": {
                "options": [
                    {"name": "Display"},
                    {"name": "Video"},
                    {"name": "Native"},
                    {"name": "Other"},
                ]
            }
        },
        "Pricing Model": {
            "select": {
                "options": [{"name": "Fixed"}, {"name": "CPM"}, {"name": "CPC"}, {"name": "Other"}]
            }
        },
        "Expected Cost": {"number": {"format": "number"}},
        "Expected Impressions": {"number": {"format": "number"}},
        "Expected View Rate": {"number": {"format": "number"}},
        "Expected CTR": {"number": {"format": "number"}},
        "Impressions Sigma %": {"number": {"format": "percent"}},
        "View Rate Sigma %": {"number": {"format": "percent"}},
        "CTR Sigma %": {"number": {"format": "percent"}},
    },
    "activations": {
        "Cost": {"number": {"format": "number"}},
        "Actual Impressions": {"number": {"format": "number"}},
        "Actual Video Views": {"number": {"format": "number"}},
        "Actual Clicks": {"number": {"format": "number"}},
        "Performance Notes": {"rich_text": {}},
    },
    "products": {
        "Average Purchase Amount": {"number": {"format": "number"}},
        "Gross Margin %": {"number": {"format": "percent"}},
        "Holding Period": {"number": {"format": "number"}},
        "Value Currency": {
            "select": {"options": [{"name": "EUR"}, {"name": "GBP"}, {"name": "USD"}]}
        },
    },
}


REMOVE_PROPERTIES = {
    "inventory": {
        "Active",
        "Pricing Model",
        "Manual Expected Cost",
        "Manual Expected Impressions",
        "Manual Expected View Rate",
        "Manual Expected CTR",
        "Manual Cost P25",
        "Manual Cost P75",
        "Manual Impressions P25",
        "Manual Impressions P75",
        "Manual View Rate P25",
        "Manual View Rate P75",
        "Manual CTR P25",
        "Manual CTR P75",
        "Cost Sigma %",
    },
    "activations": {
        "Expected Cost",
        "Actual Cost",
        "Manual Expected Cost",
    },
    "products": {
        "LTV",
        "Net Margin Bps",
        "Expected Holding Period",
        "Expected Holding Period Unit",
        "Holding Period Unit",
    },
}


def headers() -> dict[str, str]:
    token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_API_TOKEN")
    if not token:
        raise RuntimeError("NOTION_API_KEY or NOTION_API_TOKEN is not set.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def request(path: str, *, method: str = "GET", body: Any = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{NOTION_API}{path}", data=payload, method=method, headers=headers()
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Notion HTTP {exc.code} for {path}: {detail}") from exc
    return json.loads(raw) if raw else {}


def source_schema(source_id: str) -> dict[str, Any]:
    return request(f"/data_sources/{source_id}")


def ensure_source(name: str, source_id: str) -> dict[str, Any]:
    before = source_schema(source_id)
    existing = set(before.get("properties", {}))
    additions = {
        prop_name: definition
        for prop_name, definition in MODEL[name].items()
        if prop_name not in existing
    }
    removals = {
        prop_name: None
        for prop_name in REMOVE_PROPERTIES.get(name, set())
        if prop_name in existing and prop_name not in MODEL[name]
    }
    changes = {**additions, **removals}
    if changes:
        request(f"/data_sources/{source_id}", method="PATCH", body={"properties": changes})
    after = source_schema(source_id)
    after_names = set(after.get("properties", {}))
    missing = sorted(set(MODEL[name]) - after_names)
    still_present = sorted(set(removals) & after_names)
    if missing or still_present:
        raise RuntimeError(
            f"{name}: schema update incomplete; missing={missing}, still_present={still_present}"
        )
    return {
        "source": name,
        "source_id": source_id,
        "title": "".join(t.get("plain_text", "") for t in after.get("title", [])),
        "added": sorted(additions),
        "removed": sorted(removals),
        "property_count": len(after_names),
        "required_model_fields_present": True,
    }


def main() -> int:
    result = [ensure_source(name, DATA_SOURCES[name]) for name in MODEL]
    print(json.dumps({"status": "ok", "data_sources": result}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
