from planner.simulation import summarise


def test_fixed_cost_per_conversion_falls_as_conversions_rise():
    rows = [
        {"cost": 100.0, "conversions": conversions, "cost_per_conversion": 100.0 / conversions}
        for conversions in (1.0, 2.0, 4.0, 8.0)
    ]
    result = summarise(rows)["cost_per_conversion"]
    assert result["q1"] < result["median"] < result["q3"]
    assert result["median"] == 37.5
