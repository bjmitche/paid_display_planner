from planner.models import normalise_campaign, normalise_product


def test_rollup_relation_ids_are_normalised():
    page = {
        "id": "campaign-1",
        "properties": {
            "Campaign name": {"type": "title", "title": [{"plain_text": "Campaign"}]},
            "Activations": {"type": "relation", "relation": []},
            "Budget": {"type": "number", "number": 1000},
            "Budget currency": {"type": "select", "select": {"name": "GBP"}},
            "Product(s)": {
                "type": "rollup",
                "rollup": {
                    "type": "array",
                    "array": [
                        {"type": "relation", "relation": [{"id": "product-1"}]},
                        {"type": "relation", "relation": [{"id": "product-2"}]},
                    ],
                },
            },
        },
    }
    campaign = normalise_campaign(page)
    assert campaign.product_ids == ("product-1", "product-2")


def test_product_holding_period_is_loaded_from_holding_period():
    product = normalise_product(
        {
            "id": "product-1",
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Product"}]},
                "Average Purchase Amount": {"type": "number", "number": 3500},
                "Gross Margin %": {"type": "number", "number": 0.003},
                "Holding Period": {"type": "number", "number": 4.5},
                "Value Currency": {"type": "select", "select": {"name": "EUR"}},
            },
        }
    )
    assert product.holding_period == 4.5
