from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, NamedTuple

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

DEFAULT_DATA_SOURCE_IDS = {
    "campaigns": "98e0b012-5c8b-45ee-838a-02396f971f9d",
    "inventory": "2d95575d-d8f1-807e-bd84-000bf7007053",
    "activations": "2dd5575d-d8f1-805c-a94f-000b33d68795",
    "products": "2fd5575d-d8f1-800a-b94e-000bb2b0eade",
}

REQUIRED_PROPERTIES: dict[str, dict[str, str]] = {
    "campaigns": {
        "Campaign name": "title",
        "Activations": "relation",
        "Stage": "status",
        "Budget": "number",
        "Budget currency": "select",
        "Objective": "rich_text",
    },
    "inventory": {
        "Name": "title",
        "Channel": "select",
        "Format": "select",
        "Pricing Model": "select",
        "Expected Cost": "number",
        "Expected Impressions": "number",
        "Expected View Rate": "number",
        "Expected CTR": "number",
        "Impressions Sigma %": "number",
        "View Rate Sigma %": "number",
        "CTR Sigma %": "number",
    },
    "activations": {
        "Name": "title",
        "Status": "status",
        "Inventory": "relation",
        "Product": "relation",
        "Cost": "number",
        "Actual Impressions": "number",
        "Actual Video Views": "number",
        "Actual Clicks": "number",
        "Performance Notes": "rich_text",
    },
    "products": {
        "Name": "title",
        "Average Purchase Amount": "number",
        "Gross Margin %": "number",
        "Holding Period": "number",
        "Value Currency": "select",
    },
}


class DataSourceResult(NamedTuple):
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
    campaigns_id: str = DEFAULT_DATA_SOURCE_IDS["campaigns"],
    inventory_id: str = DEFAULT_DATA_SOURCE_IDS["inventory"],
    activations_id: str = DEFAULT_DATA_SOURCE_IDS["activations"],
    products_id: str = DEFAULT_DATA_SOURCE_IDS["products"],
) -> NotionClient:
    return NotionClient(
        token,
        {
            "campaigns": campaigns_id,
            "inventory": inventory_id,
            "activations": activations_id,
            "products": products_id,
        },
    )


def client_from_environment() -> NotionClient:
    token = os.environ.get("NOTION_API_TOKEN") or os.environ.get("NOTION_API_KEY")
    return client_from_values(
        token or "",
        campaigns_id=os.environ.get(
            "CAMPAIGNS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["campaigns"]
        ),
        inventory_id=os.environ.get(
            "INVENTORY_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["inventory"]
        ),
        activations_id=os.environ.get(
            "ACTIVATIONS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["activations"]
        ),
        products_id=os.environ.get("PRODUCTS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_IDS["products"]),
    )
