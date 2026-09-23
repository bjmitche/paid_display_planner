from planner.selection import resolve_choice_index


def test_stale_product_name_falls_back_to_default() -> None:
    names = ["Current Account", "Credit Card"]
    assert resolve_choice_index("Deleted Product", names, default_index=1) == 1


def test_valid_product_name_keeps_its_index() -> None:
    names = ["Current Account", "Credit Card"]
    assert resolve_choice_index("Credit Card", names, default_index=0) == 1
