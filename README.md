# Paid Display Planner

Streamlit MVP for modelling paid-display activation performance and campaign economics.

## Current status

- Streamlit hello-world app is available in `app.py`.
- Notion data model has been implemented in the existing Inventory, Activations, and Products data sources.
- Notion read verification and campaign modelling are next.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
streamlit run app.py
```

## Streamlit Community Cloud

Deploy `app.py` from the repository root. Configure the values from `.streamlit/secrets.toml.example` in the Streamlit Community Cloud Secrets panel. Never commit the real Notion token.

## Scope boundaries

The MVP is read-only against Notion. It does not write to Notion, save scenarios, run scheduled refreshes, model probabilistic LTV, or implement advanced correlations.
