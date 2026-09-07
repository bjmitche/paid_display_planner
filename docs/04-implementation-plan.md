# Paid Display Planner — Implementation Plan

## Objective

Deliver a usable internal Streamlit MVP that starts with Campaign selection, pre-loads the Campaign's existing Activations, applies Inventory performance expectations and Product LTV, runs a Monte Carlo simulation, and reports activation-level and campaign-level quartiles for conversions, flows, LTV value, cost, and ROI.

## Scope boundary

Included:

- Read-only Notion integration for Campaigns, Inventory, Activations, and Products.
- Campaign-first activation loading through existing Notion relations.
- Historical median performance with fallback Inventory assumptions.
- Deterministic Activation cost using Fixed, CPM, or CPC Pricing Model.
- Explicit target-currency normalisation using user-provided FX rates.
- Deterministic Product LTV and average purchase amount.
- Manual conversion rates and Sigma % inputs.
- Monte Carlo simulation with reproducible seed support.
- Activation-level and campaign-level quartile outputs.
- Streamlit tables and charts.
- Automated local tests and live read-only verification.
- Streamlit Community Cloud deployment readiness.

Deferred:

- Notion write-back.
- Saved scenarios.
- Scheduled refresh.
- Probabilistic LTV.
- Advanced correlations.
- Complex authentication.
- Production design system.

## Kanban workflow

Cards move through:

```text
Backlog → Ready → In Progress → Review → Done
                         ↘ Blocked
```

A card can enter `Done` only when its acceptance evidence is recorded. `Blocked` cards must state the missing dependency or decision.

## Workstreams and acceptance criteria

### A. Repository and delivery

Required:

- Repository is clean and tracks `origin/main`.
- CI runs lint and tests on pushes and pull requests.
- Streamlit Community Cloud configuration is documented.
- Secrets are never committed.

Acceptance evidence:

```text
ruff check .
pytest -q
```

### B. Notion data layer

Required:

- Load all four data sources.
- Preserve Notion page IDs.
- Parse title, select/status, number, date, relation, multi-select, rollup, and rich text values as needed.
- Resolve Campaign `Activations` relation IDs to Activation records.
- Resolve Activation `Inventory` and `Product` relation IDs.
- Report missing relations and incomplete records.

Acceptance evidence:

- Fixture tests pass.
- Live verification reports row counts and zero missing required properties/type mismatches.

### C. Inventory estimation

Required:

- Use Inventory Expected fields when no eligible finished Activation exists.
- Use historical median when eligible finished Activations exist.
- Use historical dispersion when credible.
- Use Inventory Sigma % for new/sparse placements.
- Keep rates bounded between 0 and 1.

Acceptance evidence:

- Tests cover zero history, one observation, sparse history, and sufficient history.

### D. Cost and currency model

Required:

- Fixed cost: Activation Cost.
- CPM cost: Activation Cost × impressions / 1,000.
- CPC cost: Activation Cost × clicks.
- No cost uncertainty.
- Require Activation Currency.
- Require target currency and explicit FX rates for non-target currencies.
- Convert cost, flows, and LTV value before campaign aggregation and ROI.

Acceptance evidence:

- Unit tests cover all pricing models, missing FX, same-currency conversion, and mixed-currency campaigns.

### E. Simulation

Required:

- Simulate impressions, view rate, CTR, and conversion rates.
- Use fixed seed support.
- Calculate views, clicks, conversions, flows, LTV value, deterministic cost, and ROI per iteration.
- Aggregate campaign ROI as total LTV value / total cost per iteration.
- Produce Q1, median, Q3 and retain P10/P90 where useful.

Acceptance evidence:

- Fixed-seed repeatability test.
- Boundary and invalid-input tests.
- Campaign ROI aggregation test.

### F. Streamlit UI

Required:

- Campaign selector.
- Pre-loaded Activation selector.
- Product selector.
- Target currency and FX inputs.
- Conversion rate and Sigma % inputs.
- Run simulation action.
- Activation and campaign result tables.
- Conversion, flow, and ROI charts.
- Notion verification/data-quality panel.

Acceptance evidence:

- App starts locally.
- Streamlit health endpoint returns `200 ok`.
- Manual smoke test completes the full journey.

## Dependency order

```text
Notion schema and IDs
  → Notion normalisation and relation resolution
  → estimation and economics model
  → simulation and reporting
  → Streamlit UI
  → local/live verification
  → Community Cloud deployment
```

## Promotion gates

- Do not write to Notion.
- Do not commit secrets.
- Do not deploy until local tests, lint, and live read verification pass.
- Do not claim production success until the deployed app's Verify Notion data action has been run.
