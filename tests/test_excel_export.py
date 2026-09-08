from io import BytesIO

from openpyxl import load_workbook

from planner.excel_export import build_workbook
from planner.models import Activation, Campaign, Inventory, Product


def test_build_workbook_populates_template():
    activation = Activation("a", "Activation", "Done", "i", "p", 100, "EUR", None, None, None)
    inventory = Inventory("i", "Inventory", "Display", "Fixed", 100, 1000, 0, 0.01, 0.1, 0.1, 0.1)
    product = Product("p", "Product", 1000, None, "EUR", 0.01, 2)
    rows = [
        {
            "impressions": 1000.0,
            "views": 0.0,
            "clicks": 10.0,
            "conversions": 1.0,
            "cost": 100.0,
            "flows": 1000.0,
            "value": 20.0,
            "roi": 0.2,
        }
        for _ in range(3)
    ]
    campaign_rows = [{**row, "cost_per_conversion": 100.0} for row in rows]
    workbook = build_workbook(
        Campaign("c", "Campaign", ("a",), None, None, "EUR"),
        [activation],
        {"i": inventory},
        {"p": product},
        {"p": product},
        {"i": [activation]},
        {"a": (0.0, 0.0, 0.01, 0.1)},
        "EUR",
        {},
        3,
        [(activation, rows)],
        campaign_rows,
    )
    assert workbook[:2] == b"PK"
    assert len(workbook) > 100_000
    loaded = load_workbook(BytesIO(workbook), data_only=False)
    assert loaded.sheetnames == [
        "Model Inputs & Assumptions",
        "Performance Summary",
        "Activation Detail",
        "Simulation Detail",
    ]
    assert loaded["Model Inputs & Assumptions"]["C5"].value == "Campaign"
