# MediaPulse — Power BI, DAX & Business Intelligence Interview Guide

**Role Target:** Wipro Analyst L1 (Job ID: 218535) — Business Analyst / Data Analyst (Media & BI)  
**Project Context:** MediaPulse — Media Performance & Audience Analytics  
**Focus Areas:** Semantic Modeling, DAX Engineering, Grain Resolution, Power Query M, Performance Optimization, and Media Business Interpretation  

---

## 1. Dimensional Modeling & Architecture

### Q01: In MediaPulse, why did you choose a Star Schema over a normalized Snowflake Schema or a single flat denormalized table?
**Answer:**  
In enterprise Power BI solutions, a **Star Schema** provides the optimal balance between performance, clarity, and metric accuracy:
1. **Vs. A Flat Denormalized Table (Single Wide Table):** A flat table storing all 32,265 snapshots with denormalized channel and video attributes would duplicate video-level metadata (such as titles, publication timestamps, and tags) across every snapshot row. More critically, calculating unique video reach would require complex, slow `DISTINCTCOUNT` and `CALCULATE` operations on every visual, and naive aggregations like `SUM(views)` would catastrophically overcount audience reach.
2. **Vs. A Normalized Snowflake Schema:** A pure snowflake schema would split `channels` into network hierarchies or separate `categories` into sub-genres, creating multiple relational hops. In Power BI’s in-memory VertiPaq engine, multi-hop snowflaking degrades cross-filtering performance and introduces relationship ambiguity.
3. **The Star Schema Solution:** MediaPulse implements 4 Dimensions (`DimCategory`, `DimChannel`, `DimVideo`, `DimDate`) radiating around 1 Fact Table (`FactTrendingSnapshot`). Single-direction 1-to-many relationships ensure deterministic filter propagation, sub-second visual rendering, and intuitive self-service reporting.

---

### Q02: What was the most critical grain challenge in this media dataset, and how did you resolve it in your semantic model?
**Answer:**  
The most critical grain challenge was the **discrepancy between the Creative Asset Grain (Video Level) and the Observational Fact Grain (Daily Snapshot Level)**:
- In the cleaned catalog, there are **16,305 unique videos**, but **32,265 daily trending snapshots** because persistent titles remain on the trending list across multiple days.
- **The Catastrophic View Double-Counting Issue:** Snapshot views are cumulative point-in-time metrics. If a developer authors a naive measure like `SUM(FactTrendingSnapshot[views])`, Power BI accumulates cumulative daily views across consecutive days, yielding **30,827,205,597 views**—an artificial inflation of **+176.54%** over true audience reach (**11,147,625,965 views**).
- **The Architectural Solution:** We implemented a two-tier approach:
  1. *Reporting View Pre-Aggregation:* `vw_dim_video` pre-computes each video’s canonical lifetime peak reach (`MAX(views)`), peak interactions, and lifetime engagement rate.
  2. *Grain-Aware Dynamic DAX:*
     ```dax
     Sum of Per-Video Peak Views = 
     IF(
         ISFILTERED(DimDate[full_date]),
         SUMX(DimVideo, CALCULATE(MAX(FactTrendingSnapshot[views]))),
         SUM(DimVideo[peak_views])
     )
     ```
     This allows fast single-column scalar aggregation in all-time contexts while dynamically evaluating windowed peak views when date slicers are applied.

---

### Q03: Why did you avoid bidirectional cross-filtering in your data model?
**Answer:**  
Bidirectional filtering is one of the leading causes of performance degradation and mathematical ambiguity in Power BI:
1. **Ambiguous Filter Paths:** Allowing filters to flow backwards from `FactTrendingSnapshot` into `DimVideo` or `DimDate` can introduce circular filter loops and unexpected visual results.
2. **Grain Bleed:** If a date slicer is applied to `FactTrendingSnapshot[trending_date]`, bidirectional filtering would force `DimVideo` to filter down to only videos that trended on that date, which would distort publication-date analysis and global denominators.
3. **VertiPaq Engine Cost:** In-memory single-direction relationships allow the VertiPaq engine to traverse bitmapped join indexes in a single scan. Bidirectional filtering forces expanded table scans and context transition loops, degrading report interactivity.

---

## 2. Advanced DAX Engineering & Filter Context

### Q04: Explain the difference between Row Context and Filter Context in DAX using a real measure from MediaPulse.
**Answer:**  
- **Row Context:** The concept of "the current row" during iteration. It does not filter other tables; it simply allows column values from the active row to be evaluated.
- **Filter Context:** The set of active filters applied to the data model from slicers, visual axes, page-level filters, and `CALCULATE()` statements.
- **Real Example in MediaPulse:**
  ```dax
  Median Video-Level Engagement Rate = 
  MEDIANX(
      FILTER(DimVideo, DimVideo[peak_views] > 0),
      DimVideo[lifetime_engagement_rate]
  )
  ```
  - `FILTER(DimVideo, ...)` creates a temporary table within the active **Filter Context** (e.g. only videos belonging to the "Comedy" category if sliced by Comedy).
  - `MEDIANX()` initiates a **Row Context**, stepping row-by-row through that filtered table to evaluate `DimVideo[lifetime_engagement_rate]`.
  - It then computes the true statistical median across those iterated values, completely eliminating outlier distortion without double-counting.

---

### Q05: Why did you use `ALLSELECTED()` instead of `ALL()` in your category and channel market share measures?
**Answer:**  
`ALL()` removes all filters from the specified table or column, regardless of where the filters originated. `ALLSELECTED()` removes filters within the visual but honors external slicers and page filters.
- **The MediaPulse Use Case:**
  ```dax
  Category Share of Unique Videos = 
  DIVIDE(
      [Total Unique Videos],
      CALCULATE([Total Unique Videos], ALLSELECTED(DimCategory)),
      0
  ) * 100
  ```
- **Why `ALLSELECTED` is required:**
  - In a horizontal bar chart displaying categories, we want each bar to represent its share of the active category selection.
  - If a user uses a category slicer to select 5 specific categories, `ALL()` would compute the share against all 17 categories in the database (causing the bars to sum to ~60%).
  - In contrast, `ALLSELECTED(DimCategory)` computes the share against the user’s selected 5 categories, ensuring the visual bars dynamically sum to exactly **100.00%**.

---

### Q06: Why did you use `MEDIANX` instead of `AVERAGEX` as the primary executive benchmark for audience engagement and view reach?
**Answer:**  
Media and social entertainment metrics follow an **extreme right-skewed (Pareto-style) distribution**:
- In the MediaPulse catalog, blockbuster titles (like *YouTube Rewind 2017* with 125.4M views and *Avengers: Infinity War* with 89.9M views) dramatically inflate the arithmetic mean peak views to **683,693 views**.
- However, the true **median peak views** across all 16,305 unique videos is **205,619 views** (a 3.32x difference).
- Similarly, for engagement rates, certain niche videos achieve engagement rates above 35% on low view counts, pulling the mean engagement rate to **2.06%**, whereas the true 50th percentile median is **0.83%**.
- **Business Rationale:** Presenting arithmetic averages to media executives would set an unrealistic expectation that an average video reaches ~680K views. The median provides the true, robust 50th percentile benchmark for typical content performance.

---

### Q07: How did you implement rolling averages in DAX when the underlying dataset has missing collection dates?
**Answer:**  
Standard DAX time intelligence functions like `DATESINPERIOD(DimDate[full_date], CurrentDate, -7, DAY)` assume continuous calendar collections.
- **The Problem:** In our historical dataset, there are **8 missing collection dates** (including an extended 6-day scraper outage from April 8 to April 13, 2018). If you use `DATESINPERIOD()`, Power BI divides the snapshot count by 7 calendar days, treating the 6 missing dates as zero, which produces an artificial downward crash in the rolling average.
- **The MediaPulse Solution:** We authored a custom rolling measure using `TOPN()` filtered on active collection dates:
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
  This bridges the gap by strictly averaging the **7 most recent collected dates**, maintaining a steady, accurate moving average of ~155 snapshots/day throughout pipeline outages.

---

### Q08: How do you handle role-playing dimensions in Power BI without duplicating tables?
**Answer:**  
In MediaPulse, the calendar dimension `DimDate` must serve two distinct analytical roles:
1. **Trending Snapshot Date:** The date a video was observed trending (Active relationship to `FactTrendingSnapshot[trending_date]`).
2. **Video Publication Date:** The date the video was originally uploaded to YouTube (Inactive relationship to `DimVideo[publish_date]`).
- **Implementation:** Instead of importing a second calendar table (`DimPublishDate`) which increases memory consumption and confuses report users, we left the relationship between `DimDate[full_date]` and `DimVideo[publish_date]` as **Inactive**.
- When analyzing upload cohorts, DAX dynamically activates the secondary path using `USERELATIONSHIP()`:
  ```dax
  Videos Published in Date Period = 
  CALCULATE(
      [Total Unique Videos],
      USERELATIONSHIP(DimDate[full_date], DimVideo[publish_date])
  )
  ```

---

## 3. Power Query, Storage Modes & Performance Optimization

### Q09: What factors drove your decision to use Import Mode over DirectQuery for MediaPulse?
**Answer:**  
| Factor | Import Mode (Selected) | DirectQuery |
|---|---|---|
| **Data Volume** | 32,265 fact rows (~10 MB) | Best for terabyte-scale enterprise lakes |
| **Engine** | In-Memory VertiPaq (Columnar) | Pushes queries to underlying relational engine |
| **Performance** | Sub-second visual rendering | Latency dependent on database load and network |
| **DAX Capabilities** | Full DAX support (`MEDIANX`, complex iterators) | Limited DAX support (no `MEDIAN`, query folding restrictions) |
| **Database Load** | Zero load during user dashboard interaction | Continuous SQL execution on every visual slice |
- **Conclusion:** Because this historical trending collection is static and small, Import Mode is the industry-standard choice, providing blazing-fast response times and unconstrained DAX functionality.

---

### Q10: How does VertiPaq columnar compression work, and how did you optimize memory consumption in this model?
**Answer:**  
Power BI’s VertiPaq engine compresses data columnar rather than row-based using three techniques:
1. **Value Encoding:** Subtracts the minimum value to store smaller integer deltas.
2. **Dictionary Encoding:** Replaces strings with compact integer IDs.
3. **Run-Length Encoding (RLE):** Compresses repeated consecutive values.
- **MediaPulse Optimizations:**
  - *High-Cardinality Column Pruning:* We excluded massive unstructured text fields (such as `description` and `tags`) from the reporting import model, leaving them in MySQL for ad-hoc search.
  - *Data Type Optimization:* Converted date-times to integer dates where time precision was unnecessary (`publish_date`, `trending_date`).
  - *Pre-Aggregating Complex Measures:* Encapsulating `days_to_first_trend` and `peak_views` in `vw_dim_video` eliminated the need for memory-heavy calculated columns in Power BI.
  - *Result:* Achieved a **4.2x compression ratio**, reducing the entire semantic model to under **3.0 MB in memory**.

---

### Q11: What is Query Folding in Power Query, and why is it important?
**Answer:**  
**Query Folding** is the ability of Power Query to translate M transformations (such as filtering rows, removing columns, or joining tables) into a single native SQL statement executed directly by the source database engine.
- **Why it matters:**
  1. Offloads computation to the database server (leveraging indexes).
  2. Drastically reduces network transfer by transferring only filtered, required rows.
  3. Accelerates Power BI scheduled refresh times.
- In MediaPulse, our M queries connect to pre-built MySQL reporting views (`vw_dim_video`, `vw_dim_category`), ensuring that joins and aggregations fold completely into MySQL’s query optimizer.

---

## 4. Business Acumen & Executive Stakeholder Communication

### Q12: Walk me through Page 1 of your dashboard. How does it serve an executive audience?
**Answer:**  
Page 1 is the **Executive Overview**, designed specifically for senior media executives:
1. **Top KPI Strip:** Immediately establishes scale: **16,305 unique videos**, **32,265 trending snapshots**, **1,423 publishing channels**, **17 categories**, and **205 observed dates**.
2. **Visual 1 (Daily Trending Activity Line Chart):** Displays collection stability (~150-200 snapshots/day) alongside the 7-observed-day moving average.
3. **Visual 2 (Top 10 Categories Bar Chart):** Instantly communicates supply concentration: **Entertainment (46.35%)** and **News & Politics (15.37%)** dominate over 61% of all trending content.
4. **Visual 3 (Monthly Trending Activity Column Chart):** Tracks monthly volume growth with tooltips explaining MoM changes.
5. **Collection Coverage Callout:** Proactively informs executives that 8 missing collection dates reflect scraper downtime rather than zero trending activity, demonstrating high analytical integrity.

---

### Q13: In your analysis, you found that videos with disabled comments had 40.7% lower peak views. Would you advise creators to enable comments to increase views?
**Answer:**  
**No, absolutely not.** That would be confusing **correlation with causation**:
1. **Confounding by Content Genre:** Media types that disable comments (such as broadcast news updates, government public health advisories, and corporate announcements) inherently have lower view ceilings than entertainment trailers or viral music videos.
2. **Reverse Causation:** Creators and media brands often disable comments *defensively after* experiencing severe public backlash, negative reception, or coordinated spam. In those instances, low views and poor reception caused comment disabling, rather than comment disabling causing low views.
3. **Executive Communication:** A Senior Analyst must explicitly caution stakeholders against interpreting observational associations as algorithmic penalties. Disabling comments should remain an editorial and community moderation decision.

---

### Q14: What actionable advice would you provide to a commercial media brand releasing a new video based on your findings?
**Answer:**  
Based on our verified findings, I would deliver three concrete strategic recommendations:
1. **The 48-Hour Promotional Blitz:** **96.41%** of all trending titles entered the trending feed within 48 hours of release (median = 1.0 day). External marketing, paid media, and social pushes must concentrate in the first 24–48 hours to trigger algorithmic momentum; post-48-hour promotional spend yields diminishing trending returns.
2. **Targeting Prime-Time Upload Windows:** Peak uploads in India cluster between **08:30 and 12:30 IST (03:00 to 07:00 UTC)**, allowing content to accumulate initial velocity before the afternoon and evening viewership surge.
3. **Engagement-Focused Campaigns in High-Involvement Niches:** If the business goal is audience engagement rather than raw reach, target **Comedy (2.68% median ER)** or **Science & Technology (1.92% median ER)** over mass-market Entertainment (0.78% median ER).

---

### Q15: How did you validate that your Power BI measures produce 100% accurate results?
**Answer:**  
We enforced a multi-layered automated QA framework:
1. **Three-Way Mathematical Parity:** Every DAX measure was cross-reconciled against direct MySQL 8.0 SQL queries and Python Pandas calculations across 10 validation scenarios (documented in `powerbi/validation/kpi_reconciliation.md`).
2. **Automated Pytest Suite:** We authored `tests/test_powerbi_metrics.py`, running 11 automated unit and integration tests covering row counts, non-double-counting guards, median engagement rates, trending velocity denominators, and tied channel ranks.
3. **Full Project Regression:** Running the complete test suite confirmed **82 passed / 0 failed / 0 skipped** across all project modules.
4. **Validation Transparency:** We maintain strict audit transparency: distinguishing SQL-validated, Python-validated, DAX-reviewed, and Power BI Desktop-validated assets.
