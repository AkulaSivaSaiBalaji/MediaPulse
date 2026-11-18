# MediaPulse — Power BI Dashboard Design Specification

## 1. Executive Visual Standards & Design System

The MediaPulse Power BI report follows enterprise design standards suitable for executive media presentations and senior data analyst portfolio audits.

### Visual Palette & Styling
- **Canvas Dimensions:** 1280 × 720 (16:9 standard).
- **Background Color:** Off-white / neutral `#F8F9FA`.
- **Card Background:** Pure white `#FFFFFF` with subtle 1px border `#E0E0E0` and gentle shadow.
- **Primary Accent (Navy/Brand):** `#1B2A4A` (Headings, primary bars, key metric titles).
- **Secondary Accent (Teal/Action):** `#008080` / `#0E86D4` (Highlights, active slicers, trend lines).
- **Neutral Supporting:** `#6C757D` (Axis labels, grid lines, subtitles).
- **Alert / Highlight:** `#D9534F` (Outage indicators, missing collection dates).
- **Typography:** Segoe UI (Standard Power BI system font).
  - Page Titles: 18pt Bold `#1B2A4A`.
  - Section Headings: 13pt Semi-Bold `#1B2A4A`.
  - KPI Big Number (Callout): 24pt Bold `#1B2A4A`.
  - Axis & Data Labels: 9pt Regular `#495057`.

---

## 2. Page 1: Executive Overview

### Objective
Provide C-suite and media executives with an immediate macro-level orientation of the YouTube India trending landscape, content distribution, and temporal activity.

### Layout Grid & Visual Placement

```
+---------------------------------------------------------------------------------------------------+
|  MediaPulse — YouTube India Media Performance & Audience Analytics                   [Date Slicer] |
+---------------------------------------------------------------------------------------------------+
|  [KPI 1: Videos]  |  [KPI 2: Snapshots]  |  [KPI 3: Channels]  |  [KPI 4: Categories]  | [Dates]   |
|      16,305       |        32,265        |       1,423         |          17           |   205     |
+---------------------------------------------------------------------------------------------------+
|  Visual 1: Daily Trending Snapshot Activity (Line Chart)               | Visual 2: Top Categories |
|  - X: DimDate[full_date]                                              |  - Y: category_title     |
|  - Y: [Daily Trending Snapshot Count]                                 |  - X: Total Videos       |
|  - Line: [Rolling 7-Observed-Date Snapshot Average]                   |  - Type: Horiz Bar Chart |
+-----------------------------------------------------------------------+--------------------------+
|  Visual 3: Monthly Observed Trending Activity (Column Chart)          | Visual 4: Coverage Callout|
|  - X: DimDate[year_month_label]                                       |  - 205 of 213 days       |
|  - Y: [Daily Trending Snapshot Count]                                 |  - 8 missing dates noted |
|  - Tooltip: MoM Change & MoM %                                        |  - Category Slicer       |
+---------------------------------------------------------------------------------------------------+
```

### Visual Specifications
1. **KPI Callout Cards (5 Tiles Across Top):**
   - Tile 1: `[Total Unique Videos]` (16,305)
   - Tile 2: `[Total Trending Snapshots]` (32,265)
   - Tile 3: `[Total Channels]` (1,423)
   - Tile 4: `[Total Categories]` (17)
   - Tile 5: `[Observed Trending Dates]` (205)
2. **Visual 1: Daily Trending Snapshot Activity:**
   - Visual Type: Line Chart.
   - Values: `[Daily Trending Snapshot Count]`, `[Rolling 7-Observed-Date Snapshot Average]`.
   - Business Purpose: Track daily collection volume; highlight stability (~150-200 snapshots/day) and collection gaps.
3. **Visual 2: Top 10 Categories by Unique Videos:**
   - Visual Type: Horizontal Bar Chart (Sorted Descending).
   - Category: `DimCategory[category_title]`.
   - Value: `[Total Unique Videos]`.
   - Highlight: Entertainment (7,557) and News & Politics (2,506) dominate the catalog.
4. **Visual 3: Monthly Trending Observations & Growth:**
   - Visual Type: Clustered Column Chart.
   - Category: `DimDate[year_month_label]` (Sorted chronologically by `year_month_sort`).
   - Value: `[Daily Trending Snapshot Count]`.
   - Tooltips: `[Month-over-Month Snapshot Count Change]`, `[Month-over-Month Snapshot Count Change Percentage]`.
5. **Visual 4: Data Quality & Collection Coverage Callout:**
   - Visual Type: Text / Multi-Row Card.
   - Text: *"Coverage Audit: 205 snapshot dates collected across 213 calendar days (96.2% temporal coverage). 8 uncollected dates (Jan 10-11, Apr 8-13, 2018) reflect scraper downtime, not zero trending activity."*

---

## 3. Page 2: Content & Engagement Analytics

### Objective
Analyze creative asset engagement efficiency, algorithmic induction velocity, audience persistence, and publication timing.

### KPI Cards
- `[Median Video-Level Engagement Rate]`: **0.83%** (Authoritative unskewed baseline).
- `[Average Per-Video Peak Views]`: **683.7K views**.
- `[Average Days to First Observed Trending]`: **1.31 days**.
- `[Percentage First Observed Trending Within 2 Days]`: **96.41%**.

### Visual Specifications
1. **Visual 1: Category Engagement Benchmark:**
   - Visual Type: Horizontal Bar Chart.
   - Axis: `DimCategory[category_title]`.
   - Value: `[Median Video-Level Engagement Rate]`.
   - Insight: Higher engagement in high-involvement genres (Comedy, Science & Technology) compared to high-volume Broadcast News.
2. **Visual 2: Peak Reach vs. Engagement Intensity (Efficiency Quadrant):**
   - Visual Type: Scatter Chart.
   - X-Axis: `[Median Per-Video Peak Views]` (Logarithmic scale recommended).
   - Y-Axis: `[Median Video-Level Engagement Rate]`.
   - Bubble Size: `[Total Unique Videos]`.
   - Legend / Category: `DimCategory[category_title]`.
3. **Visual 3: Algorithmic Latency (Days to First Observed Trending):**
   - Visual Type: Column Chart.
   - Categories: Latency Bins (`Day 0`, `Day 1 - 2`, `Day 3 - 7`, `Day 8+`).
   - Value: `[Total Unique Videos]`.
   - Key Benchmark: 15,720 videos (96.41%) enter within 48 hours.
4. **Visual 4: Trending Persistence Distribution:**
   - Visual Type: Column Chart.
   - Categories: Distinct Observed Dates (`1 Day`, `2 Days`, `3 Days`, `4 Days`, `5+ Days`).
   - Value: `[Total Unique Videos]`.
   - Key Benchmark: 73.55% appear on only 1 or 2 distinct dates.
5. **Visual 5: Publication Weekday Performance:**
   - Visual Type: Clustered Column & Line Chart.
   - Shared Axis: `DimDate[weekday_name]` (Sorted chronologically by `iso_weekday_num`).
   - Column: `[Total Unique Videos]` (Upload volume).
   - Line: `[Median Per-Video Peak Views]` (Audience reach).
6. **Visual 6: Publication Hour Distribution (UTC vs. IST):**
   - Visual Type: Column Chart.
   - Axis: `DimVideo[publish_hour]`.
   - Value: `[Total Unique Videos]`.
   - Annotation: Peak upload hours occur between 03:00 and 07:00 UTC (08:30 to 12:30 IST).

---

## 4. Page 3: Channel Performance & Portfolio Diversification

### Objective
Enable talent scouts, creator partnership teams, and media planners to benchmark publishing channels, analyze portfolio depth, and evaluate audience retention.

### KPI Cards
- `[Total Channels]`: **1,423 channels**.
- `[Selected Channel Unique Videos]`: Dynamic count for selected channel.
- `[Selected Channel Per-Video Peak Views]`: Cumulative peak reach for channel.
- `[Selected Channel Median Engagement]`: Channel engagement rate benchmark.

### Visual Specifications
1. **Visual 1: Top 15 Channels by Unique Trending Videos:**
   - Visual Type: Horizontal Bar Chart.
   - Axis: `DimChannel[channel_title]`.
   - Value: `[Total Unique Videos]`.
   - Leaders: Study IQ education (169), Tarang TV (158), VikatanTV (153), etvteluguindia (153).
2. **Visual 2: Top Channels by Cumulative Per-Video Peak Views:**
   - Visual Type: Horizontal Bar Chart.
   - Axis: `DimChannel[channel_title]`.
   - Value: `[Sum of Per-Video Peak Views]`.
   - Leaders: Entertainment & film trailer hubs (T-Series, FoxStarHindi, Marvel Entertainment).
3. **Visual 3: Channel Portfolio Category Diversification:**
   - Visual Type: 100% Stacked Bar Chart.
   - Y-Axis: `DimChannel[channel_title]` (Top 20 channels).
   - X-Axis: `[Total Unique Videos]`.
   - Legend: `DimCategory[category_title]`.
   - Insight: Contrasts single-genre specialists (e.g. Study IQ education in Education) against broad media conglomerates (VikatanTV, Zee Marathi).
4. **Visual 4: Executive Channel Performance Scorecard:**
   - Visual Type: Matrix / Table.
   - Rows: `DimChannel[channel_title]`.
   - Columns:
     - Rank: `[Channel Rank by Unique Videos]`
     - Unique Trending Videos: `[Total Unique Videos]`
     - Cumulative Peak Views: `[Sum of Per-Video Peak Views]`
     - Mean Peak Views: `[Average Per-Video Peak Views]`
     - Median Engagement Rate: `[Median Video-Level Engagement Rate]`
     - Mean Trending Days: `[Average Distinct Trending Dates per Video]`
