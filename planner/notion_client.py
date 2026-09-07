from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

DEFAULT_DATA_SOURCE_IDS = {
    "inventory": "2d95575d-d8f1-807e-bd84-000bf7007053",
    "activations": "2dd5575d-d8f1-805c-a94f-000b33d68795",
    "products": "2fd5575d-d8f1-800a-b94e-000bb2b0eade",
}

REQUIRED_PROPERTIES: dict[str, dict[str, str]] = {
    "inventory": {
        "Name": "title",
        "Channel": "select",
        "Format": "select",
        "Active": "checkbox",
        "Pricing Model": "select",
        "Manual Expected Cost": "number",
        "Manual Expected Impressions": "number",
        "Manual Expected View Rate": "number",
        "Manual Expected CTR": "number",
        "Manual Cost P25": "number",
        "Manual Cost P75": "number",
        "Manual Impressions P25": "number",
        "Manual Impressions P75": "number",
        "Manual View Rate P25": "number",
        "Manual View Rate P75": "number",
        "Manual CTR P25": "number",
        "Manual CTR P75": "number",
    },
    "activations": {
        "Name": "title",
        "Status": "status",
        "Inventory": "relation",
        "Product": "relation",
        "Expected Cost": "number",
        "Actual Cost": "number",
        "Actual Impressions": "number",
        "Actual Video Views": "number",
        "Actual Clicks": "number",
        "Performance Notes": "rich_text",
    },
    "products": {
        "Name": "title",
        "Average Purchase Amount": "number",
        "LTV": "number",
        "Holding Period": "number",
        "Holding Period Unit": "select",
        "Net Margin Bps": "number",
        "Value Currency": "select",
    },
}


@dataclass(frozen=True)
class DataSourceResult:
    key: str
    data_source_id: str
    title: str
    row_count: int
    property_count: int
    missing_properties: tuple[str, ...]
    type_mismatches: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_properties and not self.type_mismatches


class NotionClient:
    def __init__(self, token: str, data_source_ids: dict[str, str] | None = None) -> None:
        if not token:
            raise ValueError("A Notion API token is required.")
        self.token = token
        self.data_source_ids = data_source_ids or DEFAULT_DATA_SOURCE_IDS.copy()

    def _request(self, path: str, *, method: str = "GET", body: Any = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            f"{NOTION_API_BASE}{path}",
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Notion HTTP {exc.code} for {path}: {detail}") from exc
        return json.loads(raw) if raw else {}

    def get_schema(self, key: str) -> dict[str, Any]:
        return self._request(f"/data_sources/{self.data_source_ids[key]}")

    def query_all(self, key: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            response = self._request(
                f"/data_sources/{self.data_source_ids[key]}/query",
                method="POST",
                body=body,
            )
            rows.extend(response.get("results", []))
            if not response.get("has_more"):
                return rows
            cursor = response.get("next_cursor")
            if not cursor:
                raise RuntimeError(f"Notion returned has_more without next_cursor for {key}.")

    def verify(self) -> list[DataSourceResult]:
        results: list[DataSourceResult] = []
        for key, expected in REQUIRED_PROPERTIES.items():
            schema = self.get_schema(key)
            properties = schema.get("properties", {})
            missing = tuple(sorted(set(expected) - set(properties)))
            mismatches = tuple(
                sorted(
                    f"{name}: expected {expected_type}, got {properties[name].get('type')}"
                    for name, expected_type in expected.items()
                    if name in properties and properties[name].get("type") != expected_type
                )
            )
            rows = self.query_all(key)
            results.append(
                DataSourceResult(
                    key=key,
                    data_source_id=self.data_source_ids[key],
                    title="".join(t.get("plain_text", "") for t in schema.get("title", [])),
                    row_count=len(rows),
                    property_count=len(properties),
                    missing_properties=missing,
                    type_mismatches=mismatches,
                )
            )
        return results


def client_from_values(
    token: str,
    *,
    inventory_id: str = DEFAULT_DATA_SOURCE_IDS["inventory"],
    activations_id: str = DEFAULT_DATA_SOURCE_IDS["activations"],
    products_id: str = DEFAULT_DATA_SOURCE_IDS["products"],
) -> NotionClient:
    return NotionClient(
        token,
        {
            "inventory": inventory_id,
            "activations": activations_id,
            "products": products_id,
        },
    )


def client_from_environment() -> NotionClient:
    token = os.environ.get("NOTION_API_TOKEN") or os.environ.get("NOTION_API_KEY")
    return client_from_values(
        token or "",
        inventory_id=os.environ.get(
            "INVENTORY_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["inventory"]
        ),
        activations_id=os.environ.get(
            "ACTIVATIONS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["activations"]
        ),
        products_id=os.environ.get(
            "PRODUCTS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["products"]
        ),
    )
