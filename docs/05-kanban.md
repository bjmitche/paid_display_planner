# Paid Display Planner — Kanban Board

Last updated: 2026-09-07

## Done

- [x] Define and implement Campaigns, Inventory, Activations, and Products Notion schema.
- [x] Add Campaign-first Notion contract and verify Campaign → Activations relation is available.
- [x] Simplify Inventory planner fields to Expected values and performance Sigma %.
- [x] Make Activation cost a single deterministic `Cost` field with `Currency`.
- [x] Add Inventory `Pricing Model` for Fixed, CPM, and CPC.
- [x] Create local Git repository and push to GitHub.
- [x] Add GitHub Actions lint/test workflow.
- [x] Add Streamlit Community Cloud deployment configuration and secrets template.
- [x] Verify live Notion schemas and rows read-only.

Evidence:

- Campaigns: 19 rows.
- Inventory: 30 rows.
- Activations: 75 rows.
- Products: 58 rows.
- Latest verified commit before this work: `79a1067`.

## In Progress

- [ ] Build the first functional campaign-first planner vertical slice.
- [ ] Integrate the pure data/economics modules into the Streamlit app.

## Done

- [x] Define and implement Campaigns, Inventory, Activations, and Products Notion schema.
- [x] Add Campaign-first Notion contract and verify Campaign → Activations relation is available.
- [x] Simplify Inventory planner fields to Expected values and performance Sigma %.
- [x] Make Activation cost a single deterministic `Cost` field with `Currency`.
- [x] Add Inventory `Pricing Model` for Fixed, CPM, and CPC.
- [x] Create local Git repository and push to GitHub.
- [x] Add GitHub Actions lint/test workflow.
- [x] Add Streamlit Community Cloud deployment configuration and secrets template.
- [x] Verify live Notion schemas and rows read-only.
- [x] Add typed Notion property/page normalisation models.
- [x] Add Campaign-to-Activations relation resolution.
- [x] Add deterministic pricing-model cost functions.
- [x] Add explicit FX conversion function with missing-rate rejection.
- [x] Add unit tests for Fixed, CPM, CPC, and FX behaviour.
- [x] Add fixed-seed Monte Carlo simulation and quartile summarisation.
- [x] Add campaign-first Streamlit controls and Notion data loading.
- [x] Add target-currency and explicit FX-rate controls.
- [x] Add activation/campaign result tables and distribution chart.

## Ready

- [ ] Add full inventory historical-estimation tests.
- [ ] Add Monte Carlo simulation and quartile reporting.
- [ ] Integrate the campaign-first Streamlit UI and charts.
- [ ] Run full live application smoke test.

## Blocked

- [ ] Streamlit Community Cloud deployment: requires one-time user-side app creation and Secrets entry.

## Deferred

- [ ] Notion write-back.
- [ ] Saved scenarios.
- [ ] Scheduled refresh.
- [ ] Probabilistic LTV.
- [ ] Advanced correlations.
- [ ] Complex authentication.
