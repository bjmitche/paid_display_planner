from planner.models import Activation, Inventory, Product
from planner.simulation import SimulationInputs, simulate_campaign, summarise
from planner.validation import validate_snapshot


def inventory(format_name="Video"):
    return Inventory("i", "Inventory", format_name, "Fixed", 10, 1000, 0.5, 0.1, 0.1, 0.1, 0.1)


def test_validation_reports_bad_relations_and_negative_metrics():
    activation = Activation(
        "a", "A", "Finished", "missing", "missing-product", -1, "EUR", -2, 0, -1
    )
    report = validate_snapshot([inventory()], [activation], [])
    assert report.rejected["activations"] == 1
    assert report.unresolved_inventory == ("missing",)
    assert report.unresolved_products == ("missing-product",)
    assert not report.ok


def test_campaign_roi_is_total_value_divided_by_total_cost():
    activations = [
        Activation("a1", "A1", "Scenario", "i", "p", 10, "EUR", None, None, None),
        Activation("a2", "A2", "Scenario", "i", "p", 20, "EUR", None, None, None),
    ]
    product = Product("p", "Product", 100, 50, "EUR")
    config = SimulationInputs(0.0, 0.0, 0.0, iterations=4, seed=3)
    rows, campaign = simulate_campaign(
        activations,
        {"i": inventory("Display")},
        {"i": []},
        {"p": product},
        {"a1": config, "a2": config},
    )
    assert len(rows["a1"]) == len(campaign) == 4
    assert all(row["roi"] == row["value"] / row["cost"] for row in campaign)
    assert "cost_per_conversion" in summarise(campaign)
