# Paid Display Planner

Streamlit MVP for modelling paid-display activation performance and campaign economics.

## Current status

- Functional Streamlit planner in `app.py` with read-only Notion loading, validation, simulation, quartiles, and charts.
- Notion data model is implemented in the existing Inventory, Activations, and Products data sources.

## Local setup

```bash
# Run from /Users/finfluenceranalytics/business/paid_display_planner.
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
pytest -q
PYTHONPATH=. python scripts/verify_notion_data.py  # requires NOTION_API_TOKEN
streamlit run app.py
```

The app reads `NOTION_API_TOKEN` (or Streamlit secret of the same name) and optional
`*_DATA_SOURCE_ID` overrides. It never sends a write request to Notion. Rates entered in
the UI are decimal proportions internally; displayed conversion inputs are percentages.

## Streamlit Community Cloud CD

Streamlit Community Cloud provides the deployment step. Once the GitHub repository and `main` branch are linked to an app, a push to `main` triggers a rebuild and redeploy.

### One-time setup

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Choose **Create app**.
3. Select:
   - Repository: the GitHub repository containing this project
   - Branch: `main`
   - Main file path: `app.py`
4. Open **Advanced settings** and select Python 3.11.
5. Add the following secrets in TOML format. Replace only the token value with the real Notion integration token:

```toml
NOTION_API_TOKEN = "REPLACE_WITH_THE_REAL_NOTION_INTEGRATION_TOKEN"
CAMPAIGNS_DATA_SOURCE_ID = "98e0b012-5c8b-45ee-838a-02396f971f9d"
INVENTORY_DATA_SOURCE_ID = "2d95575d-d8f1-807e-bd84-000bf7007053"
ACTIVATIONS_DATA_SOURCE_ID = "2dd5575d-d8f1-805c-a94f-000b33d68795"
PRODUCTS_DATA_SOURCE_ID = "2fd5575d-d8f1-800a-b94e-000bb2b0eade"
```

6. Deploy the app.
7. In the deployed app, load a campaign and run a simulation; confirm the Notion verification display and result charts.

The Notion token must be entered in Streamlit Community Cloud Secrets. Do not put it in GitHub, `requirements.txt`, source code, or `.streamlit/secrets.toml.example`.

No production deployment is performed by this repository workflow. A GitHub remote and
Streamlit Cloud credentials are required before an owner can deploy it.

### Ongoing deployment workflow

Use pull requests for application changes:

```text
feature branch
    ↓
GitHub Actions CI
    ↓
pull request review
    ↓
merge to main
    ↓
Streamlit Community Cloud redeploys
```

The existing `.github/workflows/ci.yml` runs lint and tests on pushes and pull requests. For a strict deployment gate, configure GitHub branch protection on `main` and require the CI check before merging. Direct pushes to `main` can redeploy before CI completes, so they should be avoided once the app is shared with users.

### Deployment smoke test

After each deployment, verify:

```text
1. The Streamlit URL loads.
2. The app displays the current MVP status.
3. Verify Notion data completes successfully.
4. Inventory, Activations, and Products show non-zero row counts.
5. No token or credential appears in the page or logs.
```


## Scope boundaries

The MVP is read-only against Notion. It does not write to Notion, save scenarios, run scheduled refreshes, model probabilistic LTV, or implement advanced correlations.
