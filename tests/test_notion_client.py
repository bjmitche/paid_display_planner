from planner.notion_client import REQUIRED_PROPERTIES


def test_required_model_is_explicit() -> None:
    assert set(REQUIRED_PROPERTIES) == {"campaigns", "inventory", "activations", "products"}
    assert REQUIRED_PROPERTIES["campaigns"]["Activations"] == "relation"
    assert REQUIRED_PROPERTIES["inventory"]["Expected CTR"] == "number"
    assert REQUIRED_PROPERTIES["inventory"]["CTR Sigma %"] == "number"
    assert REQUIRED_PROPERTIES["activations"]["Cost"] == "number"
    assert "Actual Cost" not in REQUIRED_PROPERTIES["activations"]
    assert "LTV" not in REQUIRED_PROPERTIES["products"]


def test_data_source_ids_are_stable_defaults() -> None:
    from planner.notion_client import DEFAULT_DATA_SOURCE_IDS

    assert all(len(value) == 36 for value in DEFAULT_DATA_SOURCE_IDS.values())
