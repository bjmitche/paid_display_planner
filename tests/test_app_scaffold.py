from pathlib import Path


def test_streamlit_entrypoint_exists() -> None:
    assert Path(__file__).parents[1].joinpath("app.py").is_file()


def test_streamlit_entrypoint_contains_title() -> None:
    app_source = Path(__file__).parents[1].joinpath("app.py").read_text()
    assert "Paid Display Planner" in app_source
