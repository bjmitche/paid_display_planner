# Paid Display Planner

Streamlit MVP for modelling paid-display activation performance and campaign economics.

## Current status

- Streamlit hello-world app is available in `app.py`.
- Notion data model has been implemented in the existing Inventory, Activations, and Products data sources.
- Notion read verification and campaign modelling are next.

## Local setup

```bash
# Use Python 3.11 for this project.
/Users/finfluenceranalytics/.hermes/hermes-agent/venv/bin/python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
pytest -q
PYTHONPATH=. python scripts/verify_notion_data.py
streamlit run app.py
```

## Streamlit Community Cloud CD

Streamlit Community Cloud provides the deployment step. Once the GitHub repository and `main` branch are linked to an app, a push to `main` triggers a rebuild and redeploy.

### One-time setup

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Choose **Create app**.
3. Select:
   - Repository: `bjmitche/paid_display_planner`
   - Branch: `main`
   - Main file path: `app.py`
4. Open **Advanced settings** and select Python 3.11.
5. Add the following secrets in TOML format. Replace only the token value with the real Notion integration token:

```toml
NOTION_API_TOKEN = "REPLACE_WITH_THE_REAL_NOTION_INTEGRATION_TOKEN"
INVENTORY_DATA_SOURCE_ID = "2d95575d-d8f1-807e-bd84-000bf7007053"
ACTIVATIONS_DATA_SOURCE_ID = "2dd5575d-d8f1-805c-a94f-000b33d68795"
PRODUCTS_DATA_SOURCE_ID = "2fd5575d-d8f1-800a-b94e-000bb2b0eade"
```

6. Deploy the app.
7. In the deployed app, click **Verify Notion data** and confirm that Inventory, Activations, and Products all show `OK`.

The Notion token must be entered in Streamlit Community Cloud Secrets. Do not put it in GitHub, `requirements.txt`, source code, or `.streamlit/secrets.toml.example`.

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
