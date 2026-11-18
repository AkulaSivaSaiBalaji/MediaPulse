# MediaPulse — DAX Engineering & Analytical Explanations

## 1. Architectural Overview & Design Principles

The MediaPulse Power BI solution operates on a production star schema with an authoritative disconnected measure table (`_Measures`). 

In streaming media performance analytics, naive measure authoring introduces severe mathematical errors. Specifically:
1. **Cumulative Snapshot Bias:** Daily trending lists record cumulative views. Summing raw snapshot views across 32,265 observations yields **17,548,290,147 views**, an artificial inflation of **57.4%** above the true catalog reach (**11,147,625,965 views**).
2. **Outlier Skew:** Blockbuster trailers (such as *YouTube Rewind 2017* with 125.4M views and *Avengers: Infinity War* with 89.9M views) pull the arithmetic mean peak views (**683,693 views**) to more than **3.3x the median** (**205,619 views**).
3. **Observation-Level Latency Bias:** Computing trending latency from individual snapshot rows treats persistent videos as multiple independent entries, distorting the velocity distribution.

The MediaPulse DAX library resolves each of these challenges systematically.

---

## 2. Comprehensive DAX Measure Walkthrough

### Group 1: Core Dataset KPIs

#### `Total Unique Videos`
```dax
Total Unique Videos = DISTINCTCOUNT(DimVideo[video_id])
```
- **Filter Context:** Evaluates against `DimVideo[video_id]`.
- **Grain:** Unique creative asset level.
- **Baseline Value:** **16,305 unique videos**.
- **Behavior:** Respects slicers on `DimCategory`, `DimChannel`, or publication attributes. When cross-filtered by `DimDate`, it returns the count of unique videos published or observed depending on relationship activation.

#### `Total Trending Snapshots`
```dax
Total Trending Snapshots = COUNTROWS(FactTrendingSnapshot)
```
- **Filter Context:** Evaluates against the fact table.
- **Grain:** Daily snapshot observation level.
- **Baseline Value:** **32,265 snapshots**.
- **Behavior:** Directly measures collection volume. If a date slicer is applied, returns the number of snapshot rows collected in that date range.

#### `Total Channels`
```dax
Total Channels = DISTINCTCOUNT(DimChannel[channel_id])
```
- **Filter Context:** Evaluates against `DimChannel`.
- **Baseline Value:** **1,423 channels**.
- **Behavior:** Reflects distinct publishers within the active filter scope.

#### `Total Categories`
```dax
Total Categories = DISTINCTCOUNT(DimCategory[category_id])
```
- **Filter Context:** Evaluates against `DimCategory`.
- **Baseline Value:** **17 categories**.

#### `Observed Trending Dates`
```dax
Observed Trending Dates = 
CALCULATE(
    DISTINCTCOUNT(FactTrendingSnapshot[trending_date]),
    FactTrendingSnapshot[trending_date] <> BLANK()
)
```
- **Filter Context:** Fact table observation dates.
- **Baseline Value:** **205 distinct dates** (out of 213 total calendar days).
- **Behavior:** Crucial for collection auditing: reveals that 8 collection dates are missing from the raw scraping history rather than showing zero trending activity.

---

### Group 2: Video Performance KPIs (Grain-Aware Aggregation)

#### `Sum of Per-Video Peak Views`
```dax
Sum of Per-Video Peak Views = 
IF(
    ISFILTERED(DimDate[full_date]),
    SUMX(
        DimVideo,
        CALCULATE(MAX(FactTrendingSnapshot[views]))
    ),
    SUM(DimVideo[peak_views])
)
```
- **Analytical Significance:** Resolves the fundamental grain discrepancy.
- **Performance Optimization:** 
  - In an all-time or category/channel filter context, it executes a fast scalar `SUM(DimVideo[peak_views])` against the pre-aggregated column in `vw_dim_video`.
  - In a date-filtered context (when the user selects a specific week or month of trending), `ISFILTERED(DimDate[full_date])` dynamically switches to `SUMX(DimVideo, CALCULATE(MAX(FactTrendingSnapshot[views])))`, calculating the maximum views achieved by each video *within that selected observation window*.
- **Baseline Value:** **11,147,625,965 views**.

#### `Average Per-Video Peak Views`
```dax
Average Per-Video Peak Views = 
DIVIDE(
    [Sum of Per-Video Peak Views],
    [Total Unique Videos],
    0
)
```
- **Baseline Value:** **683,693.71 views**.
- **Filter Safety:** Uses `DIVIDE(..., 0)` to guarantee zero division returns zero instead of `NaN` or `Infinity`.

#### `Median Per-Video Peak Views`
```dax
Median Per-Video Peak Views = 
IF(
    ISFILTERED(DimDate[full_date]),
    MEDIANX(
        DimVideo,
        CALCULATE(MAX(FactTrendingSnapshot[views]))
    ),
    MEDIAN(DimVideo[peak_views])
)
```
- **Analytical Significance:** In skewed media distributions, the median is the authoritative executive benchmark for typical content performance.
- **Baseline Value:** **205,619 views**.

#### `Catalog-Level Engagement Rate`
```dax
Catalog-Level Engagement Rate = 
DIVIDE(
    [Video Peak Likes] + [Video Peak Comments],
    [Sum of Per-Video Peak Views],
    0
) * 100
```
- **Definition:** Total interactions across all videos divided by total views.
- **Format:** `0.0000%`.
- **Analytical Purpose:** Macro portfolio reach efficiency.

#### `Average Video-Level Engagement Rate` & `Median Video-Level Engagement Rate`
```dax
Average Video-Level Engagement Rate = 
AVERAGEX(
    FILTER(DimVideo, DimVideo[peak_views] > 0),
    DimVideo[lifetime_engagement_rate]
)

Median Video-Level Engagement Rate = 
MEDIANX(
    FILTER(DimVideo, DimVideo[peak_views] > 0),
    DimVideo[lifetime_engagement_rate]
)
```
- **Baseline Values:** 
  - Mean Video ER: **2.0579%**
  - Median Video ER: **0.8284%**
- **Analytical Distinction:** Because certain niche videos achieve extremely high ratio spikes (e.g. 35%+ engagement on low view counts), the arithmetic mean is inflated. The `MEDIANX` measure provides the unskewed 50th percentile baseline across the 16,305 video assets.

---

### Group 3: Trending Velocity & Persistence KPIs

#### `Average Days to First Observed Trending` & `Median Days to First Observed Trending`
```dax
Average Days to First Observed Trending = 
AVERAGEX(DimVideo, DimVideo[days_to_first_trend])

Median Days to First Observed Trending = 
MEDIANX(DimVideo, DimVideo[days_to_first_trend])
```
- **Baseline Values:** Mean = **1.31 days**, Median = **1.0 day**.
- **Grain Integrity:** Evaluated strictly at the unique-video level using each video's earliest observed trending date minus publish date.

#### `Same-Day Trending Videos` & `Videos First Observed Trending Within 2 Days`
```dax
Same-Day Trending Videos = 
CALCULATE([Total Unique Videos], DimVideo[is_same_day_trending] = 1)

Videos First Observed Trending Within 2 Days = 
CALCULATE([Total Unique Videos], DimVideo[is_trending_within_2days] = 1)

Percentage First Observed Trending Within 2 Days = 
DIVIDE([Videos First Observed Trending Within 2 Days], [Total Unique Videos], 0) * 100
```
- **Baseline Values:** 
  - Same-Day: **420 videos** (**2.58%**)
  - Within 2 Days: **15,720 videos** (**96.41%**)
- **Business Insight:** Algorithmic curation in India heavily favored freshly minted content; 96.41% of all trending titles entered within 48 hours of upload.

#### `Average Distinct Trending Dates per Video`
```dax
Average Distinct Trending Dates per Video = 
AVERAGEX(DimVideo, DimVideo[distinct_trending_days])
```
- **Baseline Value:** **1.98 distinct snapshot dates**.
- **Auditing Note:** Represents distinct snapshot appearances, not continuous uninterrupted feed residency.

---

### Group 4: Category and Channel Share & Dynamic Ranking

#### `Category Share of Unique Videos`
```dax
Category Share of Unique Videos = 
DIVIDE(
    [Total Unique Videos],
    CALCULATE([Total Unique Videos], ALLSELECTED(DimCategory)),
    0
) * 100
```
- **DAX Concept:** `ALLSELECTED(DimCategory)` removes category filters within the visual but preserves external page slicers, ensuring category percentages always sum to exactly **100.00%**.

#### `Category Rank by Unique Videos` & `Channel Rank by Unique Videos`
```dax
Category Rank by Unique Videos = 
IF(
    ISINSCOPE(DimCategory[category_title]),
    RANKX(
        ALLSELECTED(DimCategory),
        [Total Unique Videos],
        ,
        DESC,
        Dense
    )
)
```
- **DAX Concept:** `ISINSCOPE()` prevents ranking totals from displaying on card visuals or grand total summary rows. `Dense` ranking ensures tied counts share the same rank without skipping subsequent integer ranks.

---

### Group 5: Time-Based Analytics & Non-Contiguous Moving Averages

#### `Month-over-Month Snapshot Count Change` & `Percentage`
```dax
Month-over-Month Snapshot Count Change = 
VAR CurrentMonthSnapshots = [Daily Trending Snapshot Count]
VAR PreviousMonthSnapshots = 
    CALCULATE(
        [Daily Trending Snapshot Count],
        DATEADD(DimDate[full_date], -1, MONTH)
    )
RETURN
    IF(
        NOT ISBLANK(CurrentMonthSnapshots) && NOT ISBLANK(PreviousMonthSnapshots),
        CurrentMonthSnapshots - PreviousMonthSnapshots,
        BLANK()
    )
```
- **DAX Concept:** `DATEADD(..., -1, MONTH)` operates cleanly across the contiguous calendar dimension `DimDate`.

#### `Rolling 7-Observed-Date Snapshot Average`
```dax
Rolling 7-Observed-Date Snapshot Average = 
VAR CurrentDate = MAX(DimDate[full_date])
VAR Last7ObservedDates = 
    TOPN(
        7,
        FILTER(
            ALL(DimDate),
            DimDate[full_date] <= CurrentDate && 
            DimDate[is_trending_snapshot_date] = 1
        ),
        DimDate[full_date],
        DESC
    )
RETURN
    IF(
        MAX(DimDate[is_trending_snapshot_date]) = 1,
        AVERAGEX(Last7ObservedDates, CALCULATE([Daily Trending Snapshot Count]))
    )
```
- **Critical Distinction:** A standard 7-calendar-day rolling average (`DATESINPERIOD`) divides by 7 days regardless of missing collection data, artificially suppressing averages during collection outages (such as April 8–13, 2018).
- **The MediaPulse Solution:** By filtering `DimDate[is_trending_snapshot_date] = 1` and selecting the `TOPN(7, ..., DESC)`, the measure calculates the moving average across the **7 most recent collected snapshot dates**, bridging gaps without mathematical distortion.
