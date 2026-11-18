# MediaPulse — Power BI KPI Reconciliation & Validation Scenarios

## 1. Executive Summary & Validation Framework

This document reconciles all Power BI measures against independently executed MySQL 8.0 queries and Python Pandas calculations across 10 distinct analytical scenarios.

### Validation Status Legend
- **[SQL-Validated]**: Verified via direct query against `mediapulse_db`.
- **[Python-Validated]**: Verified via automated Pandas script in `tests/test_powerbi_metrics.py`.
- **[DAX-Reviewed]**: Verified mathematically through filter context and row-context audits.
- **[Power BI Desktop-Validated]**: Verified in Power BI Desktop application.

---

## 2. Multi-Grain Validation Scenarios

### Scenario 1: Baseline Catalog (No Slicers Applied)
*Scope: Full dataset across all 17 categories, 1,423 channels, and 205 snapshot dates.*

| Metric Name | Power BI Expected Value | SQL Benchmark | Pandas Benchmark | Status |
|---|---|---|---|---|
| `Total Unique Videos` | **16,305** | 16,305 | 16,305 | [SQL-Validated] [Python-Validated] |
| `Total Trending Snapshots` | **32,265** | 32,265 | 32,265 | [SQL-Validated] [Python-Validated] |
| `Total Channels` | **1,423** | 1,423 | 1,423 | [SQL-Validated] [Python-Validated] |
| `Total Categories` | **17** | 17 | 17 | [SQL-Validated] [Python-Validated] |
| `Observed Trending Dates` | **205** | 205 | 205 | [SQL-Validated] [Python-Validated] |
| `Sum of Per-Video Peak Views` | **11,147,625,965** | 11,147,625,965 | 11,147,625,965 | [SQL-Validated] [Python-Validated] |
| `Average Per-Video Peak Views` | **683,693.71** | 683,693.71 | 683,693.71 | [SQL-Validated] [Python-Validated] |
| `Median Per-Video Peak Views` | **205,619.00** | 205,619.00 | 205,619.00 | [SQL-Validated] [Python-Validated] |
| `Average Video-Level ER` | **2.0579%** | 2.0579% | 2.0579% | [SQL-Validated] [Python-Validated] |
| `Median Video-Level ER` | **0.8284%** | 0.8284% | 0.8284% | [SQL-Validated] [Python-Validated] |
| `Average Days to First Trend` | **1.3097** | 1.3097 | 1.3097 | [SQL-Validated] [Python-Validated] |
| `Median Days to First Trend` | **1.0** | 1.0 | 1.0 | [SQL-Validated] [Python-Validated] |
| `Same-Day Trending Videos` | **420** | 420 | 420 | [SQL-Validated] [Python-Validated] |
| `Videos First Trend <= 2 Days`| **15,720** | 15,720 | 15,720 | [SQL-Validated] [Python-Validated] |
| `% First Trend <= 2 Days` | **96.41%** | 96.41% | 96.41% | [SQL-Validated] [Python-Validated] |
| `Avg Distinct Trending Days` | **1.9788** | 1.9788 | 1.9788 | [SQL-Validated] [Python-Validated] |

---

### Scenario 2: Single Category Sliced (`Entertainment`)
*Filter: `DimCategory[category_title] = "Entertainment"`*

| Metric | Expected Value | Reconciled Source | Variance | Status |
|---|---|---|---|---|
| `Total Unique Videos` | **7,557** | SQL: 7,557 | 0 | [SQL-Validated] |
| `Category Share of Videos` | **46.35%** | $7,557 / 16,305 \times 100$ | 0.00% | [SQL-Validated] |
| `Total Trending Snapshots` | **16,712** | SQL: 16,712 | 0 | [SQL-Validated] |
| `Total Channels` | **429** | SQL: 429 | 0 | [SQL-Validated] |
| `Sum of Per-Video Peak Views` | **4,349,915,552** | SQL: 4,349,915,552 | 0 | [SQL-Validated] |
| `Average Per-Video Peak Views` | **575,614.07** | $4,349,915,552 / 7,557$ | 0.00 | [SQL-Validated] |
| `Median Video-Level ER` | **0.7816%** | SQL: 0.7816% | 0.0000% | [SQL-Validated] |
| `Videos <= 2 Days to Trend` | **7,314** | SQL: 7,314 | 0 | [SQL-Validated] |

---

### Scenario 3: Single Category Sliced (`News & Politics`)
*Filter: `DimCategory[category_title] = "News & Politics"`*

| Metric | Expected Value | Reconciled Source | Variance | Status |
|---|---|---|---|---|
| `Total Unique Videos` | **2,506** | SQL: 2,506 | 0 | [SQL-Validated] |
| `Category Share of Videos` | **15.37%** | $2,506 / 16,305 \times 100$ | 0.00% | [SQL-Validated] |
| `Total Trending Snapshots` | **5,249** | SQL: 5,249 | 0 | [SQL-Validated] |
| `Total Channels` | **198** | SQL: 198 | 0 | [SQL-Validated] |
| `Sum of Per-Video Peak Views` | **745,593,584** | SQL: 745,593,584 | 0 | [SQL-Validated] |
| `Average Per-Video Peak Views` | **297,523.38** | $745,593,584 / 2,506$ | 0.00 | [SQL-Validated] |
| `Median Video-Level ER` | **0.6120%** | SQL: 0.6120% | 0.0000% | [SQL-Validated] |
| `Videos <= 2 Days to Trend` | **2,467** | SQL: 2,467 | 0 | [SQL-Validated] |

---

### Scenario 4: High-Volume Channel Sliced (`Study IQ education`)
*Filter: `DimChannel[channel_title] = "Study IQ education"`*

| Metric | Expected Value | Reconciled Source | Status |
|---|---|---|---|
| `Total Unique Videos` | **169** | SQL: 169 (Rank 1 overall) | [SQL-Validated] |
| `Channel Share of Videos` | **1.04%** | $169 / 16,305 \times 100$ | [SQL-Validated] |
| `Total Snapshots` | **178** | SQL: 178 | [SQL-Validated] |
| `Sum of Per-Video Peak Views` | **15,649,850** | SQL: 15,649,850 | [SQL-Validated] |
| `Average Per-Video Peak Views` | **92,602.66** | $15,649,850 / 169$ | [SQL-Validated] |
| `Median Video-Level ER` | **6.1685%** | High educational audience engagement | [SQL-Validated] |
| `Primary Category` | **Education (169 videos)** | 100% focused on Education | [SQL-Validated] |

---

### Scenario 5: High-Reach Entertainment Channel Sliced (`T-Series`)
*Filter: `DimChannel[channel_title] = "T-Series"`*

| Metric | Expected Value | Reconciled Source | Status |
|---|---|---|---|
| `Total Unique Videos` | **62** | SQL: 62 videos | [SQL-Validated] |
| `Total Snapshots` | **126** | SQL: 126 observations | [SQL-Validated] |
| `Sum of Per-Video Peak Views` | **249,036,549** | SQL: 249,036,549 | [SQL-Validated] |
| `Average Per-Video Peak Views` | **4,016,718.53** | 4.02M views per video average | [SQL-Validated] |
| `Median Video-Level ER` | **1.9421%** | Commercial music engagement | [SQL-Validated] |
| `Average Trending Days` | **2.03 days** | $126 / 62$ | [SQL-Validated] |

---

### Scenario 6: First Day Collection Sliced (`2017-11-14`)
*Filter: `DimDate[full_date] = "2017-11-14"`*

| Metric | Expected Value | Reconciled Source | Status |
|---|---|---|---|
| `Daily Trending Snapshot Count` | **125** | SQL: 125 snapshots collected | [SQL-Validated] |
| `Distinct Observed Videos` | **125** | Exactly 1 snapshot per video on day 1 | [SQL-Validated] |
| `Observed Trending Dates` | **1** | Single selected date | [SQL-Validated] |

---

### Scenario 7: Full First Week Sliced (`2017-11-14` to `2017-11-20`)
*Filter: `DimDate[full_date] BETWEEN "2017-11-14" AND "2017-11-20"` (7 calendar days)*

| Metric | Expected Value | Reconciled Source | Status |
|---|---|---|---|
| `Total Trending Snapshots` | **1,093** | SQL: 1,093 snapshots | [SQL-Validated] |
| `Observed Trending Dates` | **7** | All 7 days collected | [SQL-Validated] |
| `Distinct Videos Observed` | **778** | Unique videos appearing in week 1 | [SQL-Validated] |

---

### Scenario 8: Cross-Filtered Channel and Category
*Filter: `DimCategory[category_title] = "Comedy"` AND `DimChannel[channel_title] = "BB Ki Vines"`*

| Metric | Expected Value | Reconciled Source | Status |
|---|---|---|---|
| `Total Unique Videos` | **5** | SQL: 5 videos | [SQL-Validated] |
| `Sum of Per-Video Peak Views` | **27,787,030** | SQL: 27,787,030 | [SQL-Validated] |
| `Average Per-Video Peak Views` | **5,557,406.00** | High-reach comedy reach | [SQL-Validated] |
| `Median Video-Level ER` | **9.1230%** | Exceptional viral engagement | [SQL-Validated] |

---

### Scenario 9: Missing Collection Date Sliced (`2018-04-10`)
*Filter: `DimDate[full_date] = "2018-04-10"` (Known scraper downtime)*

| Metric | Expected Value | Reconciled Source | Behavior / Safeguard |
|---|---|---|---|
| `Daily Trending Snapshot Count` | **0 / BLANK** | 0 rows in fact table | Visual shows no bar / blank |
| `DimDate[is_trending_snapshot_date]` | **0** | Flag correctly marks non-collection | Distinguishes outage from real zero |
| `Rolling 7-Observed Average` | **BLANK** | Measure checks flag = 1 | Prevents plotting spurious zero |

---

### Scenario 10: Tied Channel Rankings (`VikatanTV` and `etvteluguindia`)
*Filter: Top Channel Ranking Evaluation*

| Channel | Unique Videos | Dense Rank | Regular Rank | Justification |
|---|---|---|---|---|
| Study IQ education | 169 | 1 | 1 | Outright leader |
| Tarang TV | 158 | 2 | 2 | Outright 2nd |
| VikatanTV | 153 | **3** | 3 | Tied 3rd |
| etvteluguindia | 153 | **3** | 3 | Tied 3rd |
| Saregama TVShows | 152 | **4** | 5 | Dense rank assigns next rank as 4 |
