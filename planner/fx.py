from __future__ import annotations

import json
import urllib.parse
import urllib.request

FX_VERSION = "fx-v1"
CURRENCIES = ("EUR", "GBP", "USD")


def fetch_fx_rates(
    target_currency: str, source_currencies: tuple[str, ...] = CURRENCIES
) -> tuple[dict[str, float], str]:
    rates: dict[str, float] = {}
    dates: set[str] = set()
    for source in source_currencies:
        if source == target_currency:
            continue
        query = urllib.parse.urlencode({"from": source, "to": target_currency})
        request = urllib.request.Request(
            f"https://api.frankfurter.app/latest?{query}",
            headers={"User-Agent": "paid-display-planner/0.1"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
        value = payload.get("rates", {}).get(target_currency)
        if value is None:
            raise RuntimeError(f"FX API returned no {source} to {target_currency} rate.")
        rates[source] = float(value)
        if payload.get("date"):
            dates.add(payload["date"])
    return rates, ", ".join(sorted(dates)) or "unavailable"
