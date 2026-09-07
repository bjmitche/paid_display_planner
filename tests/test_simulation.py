from planner.models import Activation, Inventory, Product
from planner.simulation import SimulationInputs, simulate_activation, summarise


def test_simulation_is_reproducible_with_seed():
    activation = Activation("a", "A", "Done", "i", "p", 10, "EUR", 1000, 100, 10)
    inventory = Inventory("i", "I", "Display", "Fixed", 10, 1000, 0.1, 0.01, 0.1, 0.1, 0.1)
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
