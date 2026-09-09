from planner.models import Activation, Inventory, Product
from planner.simulation import SimulationInputs, simulate_activation, summarise


def test_simulation_is_reproducible_with_seed():
    activation = Activation("a", "A", "Done", "i", "p", 10, "EUR", 1000, 100, 10)
    inventory = Inventory(
        id="i",
        name="I",
        format="Display",
        buying_model="Fixed placement fee",
        objective="Impressions",
        currency="EUR",
        cost=10,
        rate_basis="CPM",
        expected_cpm=None,
        expected_cpc=None,
        expected_cpv=None,
        cpm_sigma=None,
        cpc_sigma=None,
        cpv_sigma=None,
        expected_impressions=1000,
        expected_view_rate=0.1,
        expected_ctr=0.01,
        impressions_sigma=0.1,
        view_rate_sigma=0.1,
        ctr_sigma=0.1,
    )
    product = Product("p", "P", 100, 20, "EUR")
    inputs = SimulationInputs(0.001, 0.01, 0.1, iterations=10, seed=7)
    first = simulate_activation(activation, inventory, [], product, inputs)
    second = simulate_activation(activation, inventory, [], product, inputs)
    assert first == second
    assert set(summarise(first)) == {
        "impressions",
        "views",
        "clicks",
        "conversions",
        "cost",
        "flows",
        "value",
        "roi",
    }
