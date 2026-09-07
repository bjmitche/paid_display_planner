# Paid Display Planner — MVP User Journey

## Purpose

This document defines how Brandon, Katie, and Tom use the first Paid Display Planner MVP.

The MVP is a read-only Streamlit application deployed to Streamlit Community Cloud. It reads Inventory, Activations, and Products from Notion, accepts campaign-specific conversion assumptions, runs a Monte Carlo simulation, and reports activation-level and campaign-level performance distributions.

## Users

### Campaign planner

A user who wants to estimate the likely performance and economics of one or more paid-display activations for a selected product.

### Data owner

A user who maintains Inventory, Activations, and Products in Notion. In the MVP, the application does not write back to Notion.

## Entry conditions

The user has:

- Access to the Streamlit application URL.
- A valid Notion-backed set of Inventory, Activations, and Products.
- A campaign or scenario to evaluate.
- Conversion-rate assumptions for impressions, views, and clicks.

## Main journey

### 1. Open the application

The user opens the Streamlit URL and sees:

- Application title and version.
- A short explanation of the model.
- A data-refresh timestamp or data status message.
- A sidebar or top-level control area for campaign inputs.

The application should make clear that results are estimates, not observed outcomes.

### 2. Select the campaign

The application pre-loads the available Campaigns from Notion.

The user selects the campaign they are working on.

The application then follows the Campaign-to-Activations relations already stored in Notion and pre-loads the campaign's Activations. The user does not manually reconstruct the activation list from Inventory for the normal workflow.

The activation list should show:

- Activation name.
- Inventory placement.
- Status.
- Expected cost.
- Product, where present.
- Whether the activation has completed performance data.

The user can select or deselect the campaign's pre-loaded Activations for the projection.

### 3. Select the product and campaign assumptions

The user selects one Product, unless the Campaign already resolves to a single Product and the application can safely preselect it.

The user enters:

1. Conversion rate per impression.
2. Conversion rate per view.
3. Conversion rate per click.
4. Optional uncertainty ranges for each conversion rate.
5. Number of simulation iterations, with a sensible default.

The application then displays the selected product and activation assumptions.

### 4. Review populated assumptions

For each selected inventory item, the application displays:

- Expected cost.
- Expected impressions/reach.
- Expected view rate, where applicable.
- Expected CTR.
- Historical activation count.
- Estimation method: fallback assumption, blended, or historical.
- Q1, median, and Q3 where available.

For the selected product, the application displays:

- Product name.
- Average purchase amount.
- LTV used for the simulation.
- Holding period and net margin bps as supporting product attributes, if present.

The user can identify whether the assumptions are based on manual input or historical activations.

### 4. Validate inputs

Before running the simulation, the application checks that:

- At least one activation has been selected.
- A product has been selected.
- Cost and impressions are not negative.
- View rate and CTR are between 0 and 1 when supplied as proportions.
- Conversion rates are non-negative and within configured bounds.
- LTV is present and positive.
- Video-only metrics are not incorrectly applied to non-video placements.

Invalid inputs produce an actionable error message. The application must not silently convert invalid or missing values to zero.

### 5. Run the simulation

The user clicks **Run simulation**.

For each iteration, the application:

1. Draws cost from the selected cost distribution.
2. Draws impressions from the selected impression distribution.
3. Draws view rate for video placements.
4. Draws CTR.
5. Calculates views and clicks.
6. Applies the three manually supplied conversion rates.
7. Calculates conversions, flows, LTV value, and ROI.
8. Aggregates all selected activations into campaign-level results.

The interface shows a progress indicator or a clear completion state.

### 6. Review activation-level results

The application displays a table with one row per selected activation or placement and columns for:

- Cost: Q1, median, Q3.
- Impressions: Q1, median, Q3.
- Views: Q1, median, Q3.
- Clicks: Q1, median, Q3.
- Conversions: Q1, median, Q3.
- Flows: Q1, median, Q3.
- LTV value: Q1, median, Q3.
- ROI: Q1, median, Q3.

P10 and P90 may be available in a detail view but are not required in the primary table.

### 7. Review campaign-level results

The application displays campaign-level Q1, median, and Q3 for:

- Total cost.
- Total impressions.
- Total views.
- Total clicks.
- Total conversions.
- Total flows.
- Total LTV value.
- Campaign ROI.
- Cost per conversion.

Campaign ROI is calculated separately for every simulation iteration as:

```text
Total campaign LTV value / Total campaign cost
```

It is not calculated as the average of activation-level ROI values.

### 8. Review charts

The application displays:

- Conversion distribution.
- Flow distribution.
- ROI distribution with a zero-ROI reference line.
- Activation comparison showing median and interquartile range.

Charts must be labelled with the selected product, scenario date/time, and number of iterations where practical.

### 9. Interpret the result

The user uses the results to answer:

- Which placement is expected to produce the most conversions?
- Which placement has the strongest flow potential?
- Which placement has the most attractive ROI distribution?
- How uncertain is the result?
- What is the downside and upside range for the campaign?

The application should avoid presenting the median as a guaranteed forecast.

## Data refresh behaviour

In the MVP, data is loaded from Notion when the application starts or when the user clicks a refresh control. There is no scheduled refresh and no write-back to Notion.

The interface should show:

- Last successful read timestamp.
- Number of Inventory records loaded.
- Number of completed Activations loaded.
- Number of Products loaded.
- Any rejected or incomplete records.

## Empty and error states

The application should handle:

- No Inventory records.
- No completed historical Activations.
- No Products.
- Missing LTV.
- Missing or malformed activation metrics.
- Notion API unavailable.
- Invalid Notion credentials.
- No valid activation selected.
- Simulation failure.

Each error should state what the user can do next.

## MVP non-goals

The MVP does not:

- Write to Notion.
- Save scenarios or user-specific workspaces.
- Provide complex authentication or role-based permissions.
- Run scheduled data refreshes.
- Model probabilistic LTV.
- Model advanced correlations between performance variables.
- Provide a fully polished production design system.
- Replace Notion as the operational source of truth.

## Definition of journey completion

The journey is successful when a user can select an activation and product, enter conversion assumptions, run a simulation, and inspect activation-level and campaign-level quartiles for conversions, flows, LTV value, and ROI with charts.
