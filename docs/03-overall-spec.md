# Paid Display Planner — Streamlit MVP Overall Specification

## 1. Objective

Build a small internal web application that allows Brandon, Katie, and Tom to project the performance and economics of paid-display activations.

The application will:

- Read Inventory, Activations, and Products from Notion.
- Estimate future activation performance from manual assumptions and finished activation history.
- Allow a user to select an activation/placement and product.
- Accept campaign-specific conversion-rate assumptions.
- Run a Monte Carlo simulation.
- Report activation-level and campaign-level quartiles for conversions, flows, LTV value, and ROI.
- Display charts for interpretation.

The initial deployment target is Streamlit Community Cloud.

## 2. Scope decision

### Included in MVP

- Streamlit web interface.
- Read-only Notion integration.
- Inventory, Activation, and Product loading.
- Manual assumptions for new Inventory records.
- Historical median performance for Inventory records with finished Activations.
- Blended dispersion that becomes more historical as data accumulates.
- Deterministic product LTV.
- Manual conversion rates for impressions, views, and clicks.
- Uncertainty for media metrics and conversion rates.
- Monte Carlo simulation.
- Activation-level Q1, median, and Q3 results.
- Campaign-level Q1, median, and Q3 results.
- Conversion, flow, LTV-value, ROI, and cost-per-conversion outputs.
- Basic interactive charts.
- Local automated tests for core business logic.
- Streamlit Community Cloud deployment.

### Explicitly excluded from MVP

- Writing to Notion.
- Complex authentication workflows.
- Multiple saved users or scenarios.
- Automated daily refresh.
- Advanced correlations between simulated variables.
- Probabilistic LTV.
- A polished production design system.
- Full campaign history or scenario persistence.
- User-specific permissions.
- Automated media buying or booking.

## 3. Core business definitions

### Inventory

A reusable placement type or media opportunity that can be selected for campaign planning.

### Activation

A specific run of an Inventory placement. Finished Activations contain ex-post performance data and are used to estimate future performance.

### Product

The product promoted by the campaign. The Product supplies average purchase amount and deterministic LTV.

### Flows

For the MVP:

```text
Flows = conversions × average purchase amount
```

### LTV value

For the MVP:

```text
LTV value = conversions × product LTV
```

LTV already incorporates the product economics. The application must not apply holding period or margin a second time.

### ROI

For the MVP:

```text
ROI = LTV value / campaign cost
```

ROI is calculated per simulation iteration and then summarised into quartiles.

## 4. User inputs

The campaign planner must support the following sequence:

1. Pre-load Campaigns from Notion.
2. Select the Campaign being planned.
3. Follow the Campaign's existing `Activations` relation.
4. Pre-load the related Activations from Notion.
5. Select or deselect the Activations to include in the projection.
6. Select one Product, or safely preselect the Product when the Campaign resolves to one.
7. Enter conversion rate per impression.
8. Enter conversion rate per view.
9. Enter conversion rate per click.
10. Optionally enter P25/P75 uncertainty for each conversion rate.
11. Set the simulation iteration count.
12. Optionally set a random seed for reproducible testing.

Inventory is used to supply performance assumptions for the pre-loaded Activations. The normal user journey begins with Campaign selection, not with manually browsing all Inventory.

The application should use sensible defaults but must expose the assumptions used in the run.

## 5. Inventory estimation

### Zero historical activations

If an Inventory item has zero eligible finished Activations:

```text
Expected median = Inventory expected value
Sigma = Inventory Sigma % fallback
Method = Fallback assumption
```

The Inventory expected values are only fallback inputs. They are not intended to duplicate historical estimates.

### Historical activations

If an Inventory item has eligible finished Activations:

```text
Expected median = historical median
Sigma = historical dispersion, subject to a minimum floor
```

The metrics are:

- Cost.
- Impressions.
- View rate for video placements.
- CTR.

### Dispersion rule

For new or data-sparse Inventory, the stored Sigma % is the coefficient of variation used as the fallback dispersion. With enough historical Activations, historical dispersion takes precedence. A minimum dispersion floor prevents small samples from producing false certainty.

The application may blend historical dispersion with the stored Sigma % while the historical sample is small, but it must not require P25/P75 fields in Notion.
## 6. Simulation model

For each selected activation and each simulation iteration:

1. Draw cost.
2. Draw impressions.
3. Draw view rate for video inventory.
4. Draw CTR.
5. Calculate views.
6. Calculate clicks.
7. Apply conversion rates.
8. Calculate conversions.
9. Calculate flows.
10. Calculate LTV value.
11. Calculate activation ROI.

### Media calculations

```text
Views = impressions × view rate
Clicks = impressions × CTR
```

For non-video inventory:

```text
Views = 0
```

unless the placement explicitly supports a separate engagement measure.

### Conversion calculations

The MVP treats the three conversion rates as incremental and additive:

```text
Conversions =
    impressions × conversion rate per impression
  + views × conversion rate per view
  + clicks × conversion rate per click
```

This assumption must be visible to users because views and clicks may overlap with impressions.

### Product calculations

```text
Flows = conversions × average purchase amount
LTV value = conversions × product LTV
ROI = LTV value / cost
```

## 7. Distribution model

The MVP requires positive-value media metrics to be modelled with positive distributions, preferably lognormal:

- Cost.
- Impressions.
- Potentially views and clicks if directly modelled.

Rates must remain bounded:

- View rate.
- CTR.
- Conversion rate per impression.
- Conversion rate per view.
- Conversion rate per click.

Users should enter uncertainty as a central value plus Sigma % where needed. Sigma % is coefficient of variation and is converted internally to the distribution parameters. Historical dispersion should override the Inventory fallback Sigma % when enough observations exist.

## 8. Results

### Activation-level results

For every selected activation or placement, show Q1, median, and Q3 for:

- Cost.
- Impressions.
- Views.
- Clicks.
- Conversions.
- Flows.
- LTV value.
- ROI.

P10 and P90 may be retained in the result data for later display.

### Campaign-level results

Show Q1, median, and Q3 for:

- Total cost.
- Total impressions.
- Total views.
- Total clicks.
- Total conversions.
- Total flows.
- Total LTV value.
- Campaign ROI.
- Cost per conversion.

Campaign ROI must be calculated as:

```text
sum of activation LTV values / sum of activation costs
```

for each simulation iteration. It must not be calculated as the average of activation ROIs.

## 9. Charts

The MVP must include:

1. Campaign conversions distribution.
2. Campaign flows distribution.
3. Campaign ROI distribution with a zero-ROI reference line.
4. Activation comparison chart showing medians and interquartile ranges.

Charts must update when a new simulation is run.

## 10. Application screens and layout

A single-page Streamlit application is sufficient for MVP.

### Sidebar or input panel

- Campaign selector populated from Notion.
- Pre-loaded activation selector populated from the selected Campaign's Activations relation.
- Product selector, with safe preselection where possible.
- Conversion-rate inputs.
- Conversion-rate uncertainty inputs.
- Simulation iteration input.
- Run simulation button.
- Refresh Notion data button.

### Main area

- Data status and validation messages.
- Selected assumptions.
- Activation-level results.
- Campaign-level results.
- Charts.
- Methodology notes.

## 11. Data and integration architecture

```text
Notion Campaigns ─┐
Notion Inventory ──┼──> Streamlit data layer ──> estimation layer
Notion Activations ┤                                  ↓
Notion Products ───┘                             simulation layer
                                                     ↓
                                              results and charts
```

The application is read-only against Notion.

The Notion token and data-source IDs must be stored as Streamlit secrets and must not be committed to GitHub.

Expected secret names should be explicit, for example:

```toml
NOTION_API_TOKEN = "replace with the real Notion integration token"
INVENTORY_DATA_SOURCE_ID = "replace with the real Inventory data source ID"
ACTIVATIONS_DATA_SOURCE_ID = "replace with the real Activations data source ID"
PRODUCTS_DATA_SOURCE_ID = "replace with the real Products data source ID"
```

These are configuration names, not values to commit to the repository.

## 12. Technical stack

Recommended MVP stack:

- Python 3.11 or newer supported by the deployment target.
- Streamlit.
- Pandas.
- NumPy.
- Plotly.
- Requests or the official Notion client as appropriate.
- Pytest.
- GitHub repository.
- Streamlit Community Cloud.

The core modelling functions should be independent of Streamlit so they can be tested without credentials or a browser.

## 13. Code structure

```text
paid-display-planner/
  app.py
  planner/
    __init__.py
    notion_client.py
    schemas.py
    validation.py
    estimates.py
    distributions.py
    simulation.py
    reporting.py
  tests/
    test_validation.py
    test_estimates.py
    test_distributions.py
    test_simulation.py
    test_reporting.py
  requirements.txt
  README.md
  .gitignore
  .streamlit/
    secrets.toml.example
```

The real `secrets.toml` must never be committed.

## 14. Testing requirements

### Unit tests

Test:

- Manual assumptions with zero history.
- Historical median with one or more Activations.
- Blended dispersion at 0, 1, 3, and 6+ Activations.
- Invalid rates.
- Missing LTV.
- Zero impressions.
- Zero cost.
- Conversion calculations.
- Flow calculations.
- LTV calculations.
- Campaign ROI aggregation.
- Fixed-seed simulation reproducibility.

### Integration tests

Test against representative Notion response fixtures without requiring live credentials:

- Inventory mapping.
- Activation relation mapping.
- Product mapping.
- Finished-Activation filtering.
- Rejected-record reporting.

### Manual acceptance tests

Run the live application and verify:

1. A zero-history Inventory item uses manual assumptions.
2. An Inventory item with finished Activations uses the historical median.
3. A selected Product supplies average purchase amount and LTV.
4. The user can enter all three conversion rates.
5. Simulation completes and produces activation-level results.
6. Campaign-level results aggregate all selected Activations.
7. Campaign ROI is total LTV value divided by total cost.
8. All four charts render.
9. Invalid data produces an actionable message.
10. The deployed URL works without local files.

## 15. Deployment

The MVP is deployed through Streamlit Community Cloud from a GitHub repository.

Deployment requirements:

- Repository contains `app.py`.
- Dependencies are declared in `requirements.txt`.
- Secrets are entered in Streamlit Community Cloud settings.
- No credentials are committed to GitHub.
- The deployed app is smoke-tested after deployment.

## 16. Security and privacy boundary

The MVP uses no complex authentication workflow. The interim access decision is **URL secrecy**: the Streamlit app may be publicly reachable, but its URL will not be advertised or indexed and will be shared only with intended users.

This is not equivalent to authentication. Anyone who obtains the URL may be able to access the app. Therefore:

- Keep the GitHub repository private.
- Store the Notion token only in Streamlit Community Cloud Secrets.
- Never commit credentials to GitHub or display them in the application.
- Do not expose unnecessary Notion fields in the application.
- Do not write data back to Notion from the public app.
- Treat the URL as confidential and do not publish it in README badges, public documentation, or social posts.
- Revisit authenticated hosting before the app is used for materially sensitive data or shared beyond the intended users.

## 17. MVP acceptance criteria

The MVP is complete when:

- The deployed Streamlit URL loads successfully.
- Campaigns, Inventory, Activations, and Products can be read from Notion.
- Data-quality issues are visible to the user.
- A user can select a Campaign and see its related Activations pre-loaded.
- A user can select or deselect pre-loaded Activations and select a Product.
- Product LTV populates automatically.
- Manual conversion rates can be entered.
- Zero-history and historical estimation methods work as specified.
- Monte Carlo simulation completes successfully.
- Activation-level Q1, median, and Q3 results are shown.
- Campaign-level Q1, median, and Q3 results are shown.
- Results include conversions, flows, LTV value, and ROI.
- Charts render from the current simulation.
- Core tests pass.
- No write-back to Notion occurs.
- No secrets are present in the repository.

## 18. Deferred improvements

After the MVP has been validated, consider:

- Saved scenarios.
- Probabilistic LTV.
- Correlated media variables.
- Beta distributions for bounded rates.
- Scheduled data refresh.
- Notion write-back of approved estimates.
- Cloud Run deployment with stronger access control.
- Audit history.
- A richer campaign comparison interface.
