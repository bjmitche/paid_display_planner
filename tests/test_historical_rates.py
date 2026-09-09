from planner.economics import estimate_inventory
from planner.models import Activation, Inventory


def inventory(rate_basis: str) -> Inventory:
    return Inventory(
        id="i",
        name="Inventory",
        format="Display",
        buying_model="Algorithmic budget",
        objective="Impressions",
        currency="EUR",
        cost=1000,
        rate_basis=rate_basis,
        expected_cpm=None,
        expected_cpc=None,
        expected_cpv=None,
        cpm_sigma=None,
        cpc_sigma=None,
        cpv_sigma=None,
        expected_impressions=100000,
        expected_view_rate=0.5,
        expected_ctr=0.01,
        impressions_sigma=0.1,
        view_rate_sigma=0.1,
        ctr_sigma=0.1,
    )


def test_historical_cpm_is_median_of_actual_cost_per_impression():
    history = [
        Activation("a1", "A1", "Done", "i", "p", 100, "EUR", 10000, None, None),
        Activation("a2", "A2", "Done", "i", "p", 120, "EUR", 10000, None, None),
        Activation("a3", "A3", "Done", "i", "p", 150, "EUR", 10000, None, None),
    ]
    estimate = estimate_inventory(inventory("CPM"), history, activation_cost=1000)
    assert estimate.target_rate == 12.0
    assert estimate.target_basis == "CPM"
    assert estimate.impressions == 1000 / 12 * 1000


def test_historical_cpc_is_median_of_actual_cost_per_click():
    history = [
        Activation("a1", "A1", "Done", "i", "p", 100, "EUR", 10000, None, 100),
        Activation("a2", "A2", "Done", "i", "p", 120, "EUR", 10000, None, 100),
        Activation("a3", "A3", "Done", "i", "p", 150, "EUR", 10000, None, 100),
    ]
    estimate = estimate_inventory(inventory("CPC"), history, activation_cost=1000)
    assert estimate.target_rate == 1.2
    assert estimate.target_basis == "CPC"
