# Paid Display Planner — Notion Input Specification

## Purpose

This document defines the Notion data required by the Streamlit MVP. Notion remains the operational source of truth. The application reads data from Notion and does not write calculated values back during the MVP.

Property names below are canonical application names. Existing Notion property names may be mapped to these names during implementation, but each mapping must be explicit.

## General rules

- Every record must have a stable Notion page ID.
- Every record must have a human-readable name.
- Numeric fields must be stored as numbers, not formatted text.
- Rates must use one consistent convention. The recommended convention is decimal proportions: `0.05` means 5%.
- Currency values must identify their currency. The MVP should use one campaign currency per run.
- Missing values must remain missing; they must not be silently converted to zero.
- Finished Activations are the only records eligible for historical performance estimation.

## Inventory data source

The Inventory data source describes a reusable placement or placement type from which planned activations can be selected.

### Required Inventory properties

| Application field | Suggested Notion property | Type | Required | Description |
|---|---|---:|---:|---|
| Inventory ID | `Inventory ID` | Rich text or formula | Yes | Stable business identifier if available. Notion page ID remains the technical fallback. |
| Inventory name | `Name` | Title | Yes | Human-readable placement name. |
| Platform/channel | `Platform` | Select | Yes | Platform or channel. |
| Format | `Format` | Select | Yes | Display, video, native, sponsored, or other agreed value. |
| Active | `Active` | Checkbox or status | Yes | Whether the placement is available for planning. |
| Pricing model | `Pricing model` | Select | Yes | Fixed, CPM, CPC, CPV, or other agreed model. |
| Manual expected cost | `Manual expected cost` | Number | Yes for new inventory | Initial expected cost when no historical activation exists. |
| Manual expected impressions | `Manual expected impressions` | Number | Yes for new inventory | Initial expected impressions/reach assumption. |
| Manual expected view rate | `Manual expected view rate` | Number | Video only | Initial video view-rate assumption as a proportion. |
| Manual expected CTR | `Manual expected CTR` | Number | Yes | Initial CTR assumption as a proportion. |
| Manual cost P25 | `Manual cost P25` | Number | Yes for new inventory | Lower-quartile cost assumption. |
| Manual cost P75 | `Manual cost P75` | Number | Yes for new inventory | Upper-quartile cost assumption. |
| Manual impressions P25 | `Manual impressions P25` | Number | Yes for new inventory | Lower-quartile impressions assumption. |
| Manual impressions P75 | `Manual impressions P75` | Number | Yes for new inventory | Upper-quartile impressions assumption. |
| Manual view-rate P25 | `Manual view-rate P25` | Number | Video only | Lower-quartile view-rate assumption. |
| Manual view-rate P75 | `Manual view-rate P75` | Number | Video only | Upper-quartile view-rate assumption. |
| Manual CTR P25 | `Manual CTR P25` | Number | Yes | Lower-quartile CTR assumption. |
| Manual CTR P75 | `Manual CTR P75` | Number | Yes | Upper-quartile CTR assumption. |

### Optional Inventory properties

| Application field | Suggested Notion property | Type | Description |
|---|---|---:|---|
| Currency | `Currency` | Select | Currency for cost and flow values. |
| Minimum spend | `Minimum spend` | Number | Minimum cost constraint. |
| Typical activation duration | `Duration` | Number or rich text | Context for interpreting historical performance. |
| Notes | `Notes` | Rich text | Operational notes or caveats. |
| Video eligible | `Video eligible` | Checkbox | Explicitly identifies whether view rate applies. |

## Campaign data source

The Campaigns data source is the first-level planning selector in the application. The user selects a Campaign, and the application follows its existing relation to Activations.

### Required Campaign properties

| Application field | Notion property | Type | Required | Description |
|---|---|---:|---:|---|
| Campaign name | `Campaign name` | Title | Yes | Pre-loaded campaign selector label. |
| Activations | `Activations` | Relation | Yes | Relations to the Activations included in the campaign. |
| Stage | `Stage` | Status | Recommended | Used to identify active/plannable campaigns. |
| Budget | `Budget` | Number | Optional | Campaign budget context. |
| Budget currency | `Budget currency` | Select | Optional | Currency for the campaign budget. |
| Objective | `Objective` | Rich text | Optional | Campaign objective shown as context. |

The application must preserve the relation page IDs from `Activations`. It should not infer campaign membership from names or from Inventory relations.

### Campaign loading rules

1. Load Campaign records visible to the Notion integration.
2. Present a pre-loaded campaign list to the user.
3. When a Campaign is selected, read its `Activations` relation.
4. Match relation IDs to the full Activations result set.
5. Show unresolved relation IDs as data-quality warnings.
6. Pre-load the resolved Activations for user selection.

## Activation data source

The Activations data source contains individual runs of an Inventory placement. It contains both planning relationships and ex-post performance data.

### Required Activation properties

| Application field | Suggested Notion property | Type | Required | Description |
|---|---|---:|---:|---|
| Activation ID | `Activation ID` | Rich text or formula | Yes | Stable business identifier if available. |
| Activation name | `Name` | Title | Yes | Human-readable activation name. |
| Inventory relation | `Inventory` | Relation | Yes | Relation to exactly one Inventory record. |
| Status | `Status` | Select or status | Yes | Must include a value equivalent to `Finished`. |
| Start date | `Start date` | Date | Recommended | Activation start. |
| End date | `End date` | Date | Recommended | Activation end. |
| Actual cost | `Actual cost` | Number | Finished activations | Actual paid cost. |
| Actual impressions | `Actual impressions` | Number | Finished activations | Delivered impressions/reach. |
| Actual video views | `Actual video views` | Number | Video activations | Delivered views. |
| Actual clicks | `Actual clicks` | Number | Finished activations | Delivered clicks. |
| Actual view rate | `Actual view rate` | Number or formula | Recommended | Actual video views divided by impressions. |
| Actual CTR | `Actual CTR` | Number or formula | Recommended | Actual clicks divided by impressions. |

### Activation eligibility rules

An Activation is eligible for historical estimation only when:

1. Its status is `Finished`.
2. It relates to a valid Inventory record.
3. Actual cost is present and non-negative.
4. Actual impressions are present and non-negative.
5. Video metrics are present for video activations where view rate is required.
6. Actual clicks are present or explicitly recorded as zero.

The application should report rejected or incomplete Activations rather than silently excluding them.

### Activation-derived metrics

If Notion does not store these as properties, the application calculates:

```text
Actual view rate = actual video views / actual impressions
Actual CTR = actual clicks / actual impressions
```

Division by zero must produce a missing value and a data-quality warning, not an infinite value.

## Product data source

The Products data source provides the commercial assumptions used to value conversions.

### Required Product properties

| Application field | Suggested Notion property | Type | Required | Description |
|---|---|---:|---:|---|
| Product ID | `Product ID` | Rich text or formula | Yes | Stable business identifier if available. |
| Product name | `Name` | Title | Yes | Human-readable product name. |
| Active | `Active` | Checkbox or status | Recommended | Whether the product can be selected. |
| Average purchase amount | `Average purchase amount` | Number | Yes for flow modelling | Average amount associated with a conversion. |
| LTV | `LTV` | Number | Yes | Deterministic value per conversion used for campaign ROI. |
| Holding period | `Holding period` | Number | Recommended | Product-level supporting attribute. |
| Holding period unit | `Holding period unit` | Select | Recommended | Months or years. |
| Net margin bps | `Net margin bps` | Number | Recommended | Supporting product-level margin assumption. |
| Currency | `Currency` | Select | Recommended | Currency for purchase amount and LTV. |

### Product calculation rule

The application uses the stored Product `LTV` directly:

```text
LTV value = conversions × product LTV
```

The application must not multiply LTV by holding period or net margin again. Holding period and margin are retained as supporting attributes for transparency and future LTV governance.

Flows are calculated separately:

```text
Flows = conversions × average purchase amount
```

## Estimation methodology

### Zero historical activations

For an Inventory item with zero eligible finished Activations:

```text
Median = manual expected value
P25 = manual P25
P75 = manual P75
Method = Manual assumption
```

### Historical activations

For an Inventory item with one or more eligible finished Activations:

```text
Median = historical median
```

Dispersion is blended according to the number of eligible historical Activations:

```text
Historical weight = MIN(1, eligible activation count / 6)
Manual weight = 1 - historical weight
```

The implementation may use log-space blending for positive metrics such as cost and impressions. Rate metrics must remain within valid bounds.

### Minimum dispersion

The application should support a minimum dispersion floor so that a small number of similar Activations does not imply implausible certainty.

The floor should be configured in the application or Inventory assumptions rather than hard-coded invisibly.

## Conversion-rate inputs

Conversion rates are not required to be stored in Notion for the MVP. They are entered by the user for each campaign run:

- Conversion rate per impression.
- Conversion rate per view.
- Conversion rate per click.

Each input may have a central value and optional P25/P75 uncertainty range.

The MVP assumption is that these rates are incremental and additive:

```text
Conversions =
    impressions × conversion rate per impression
  + views × conversion rate per view
  + clicks × conversion rate per click
```

This assumption must be displayed in the application and can be revised later if the business decides to model a sequential funnel instead.

## Data-quality report

Every Notion read should produce a data-quality summary containing:

- Records read by data source.
- Records accepted.
- Records rejected.
- Missing required fields.
- Invalid numeric values.
- Duplicate business identifiers.
- Unresolved Inventory relations.
- Unresolved Product relations.
- Last successful read timestamp.

## MVP exclusions

The Notion integration does not:

- Create or update Notion records.
- Write historical estimates back to Inventory.
- Write simulation results back to Activations.
- Create new Products or Activations.
- Apply Notion database view filters.
- Depend on Notion formulas where the same value can be calculated and validated in the application.
