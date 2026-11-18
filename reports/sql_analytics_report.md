# MediaPulse — Phase 6: Advanced SQL Analytics Report

**Project:** MediaPulse — Media Performance & Audience Analytics  
**Target Role:** Wipro Analyst L1 (Job ID: 218535) — Business Analyst / Data Analyst (Media)  
**Prepared By:** MediaPulse Analytics & Database Engineering Team  
**Database Reference:** MySQL Server 8.0.46 Community (`mediapulse_db`)  
**Status:** Completed & Validated (20 Queries Executed, 67/67 Tests Passing)  

---

## 1. Executive Summary & Pre-Implementation Verification

Phase 6 marks the implementation of a production-grade SQL analytics suite developed directly against the verified MySQL 8 relational database (`mediapulse_db`). The suite addresses critical executive questions surrounding content reach, audience engagement dynamics, creator publishing cadence, and viral breakout velocity across the Indian YouTube trending ecosystem.

### Database Verification Summary:
- **Baseline Git Commit:** Executed on branch `develop` from Phase 5 commit `bed3bed`.
- **Relational Tables Audited:**
  - `categories`: **17 rows** (Official YouTube category taxonomy)
  - `channels`: **1,423 rows** (Publishing media brands, case-sensitive `utf8mb4_bin`)
  - `videos`: **16,305 rows** (Unique creative video assets)
  - `trending_snapshots`: **32,265 rows** (Longitudinal daily performance observations)
- **Constraint Compliance:** 0 orphan foreign key records, 0 duplicate `(video_id, trending_date)` pairs.

---

## 2. Portfolio Structure & Query Taxonomy

To maintain modularity and avoid redundant script duplication, the 20 analytical queries are organized into three dedicated SQL files:

| File Name | Query Range | Core SQL Concepts Demonstrated | Analytical Focus |
| :--- | :---: | :--- | :--- |
| [sql/advanced_analytics.sql](file:///D:/MediaPulse/sql/advanced_analytics.sql) | Q01 – Q08 | CTEs, `DATE_FORMAT()`, `DATEDIFF()`, `FIELD()`, `MOD()`, `CASE WHEN`, Window `SUM() OVER()` | Volume concentration, peak view reach, monthly activity, upload scheduling, viral latency, persistence, and engagement tiers. |
| [sql/window_functions.sql](file:///D:/MediaPulse/sql/window_functions.sql) | Q09 – Q14 | `ROW_NUMBER()`, `DENSE_RANK()`, `LAG()`, Window Frame `ROWS BETWEEN 6 PRECEDING`, Partitioned Window `SUM() OVER(PARTITION BY)` | Top 3 videos per category, channel genre ranks, month-over-month growth, 7-day rolling trailing velocity, Pareto view contributions. |
| [sql/business_queries.sql](file:///D:/MediaPulse/sql/business_queries.sql) | Q15 – Q20 | Double CTEs, Percentile Window Median, Conditional Aggregation, Safe `NULLIF()` Division | Publisher longevity portfolios, true median engagement rates, Day-0 viral breakouts, multi-genre channel diversification, comment disable impact, prime-time upload ROI. |

---

## 3. Top 10 Evidence-Based Analytical Findings

Each finding pairs an executive business question with verified SQL results and analytical interpretations:

### Finding 1: Mass Market Duopoly vs. Long-Tail Fragmentation
- **Business Question:** What content genres dominate the Indian digital video landscape, and how concentrated is catalog volume?
- **SQL Technique:** Common Table Expression (CTE) with `COUNT(v.video_id)` and window function `ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2)`.
- **Actual Result (Q01):**
  - **Entertainment:** 7,557 unique videos (**46.35%** market share)
  - **News & Politics:** 2,506 unique videos (**15.37%** market share)
  - **Combined Top 2:** **61.72%** of the entire trending surface
  - Long-Tail (15 other categories): Remaining 38.28% (e.g., Science & Technology: 1.85%, Gaming: 0.12%, Pets & Animals: 0.01%).
- **Business Interpretation:** Broadcast television catch-up content, film clips, and regional news networks dominate trending real estate. Media buyers seeking mass brand reach must allocate the majority of ad inventory to Entertainment and News.
- **Analytical Limitation:** Categorization reflects creator self-classification at upload and does not differentiate long-form serial television from standalone sketch comedy.
- **Reference:** [Query 01 (sql/advanced_analytics.sql)](file:///D:/MediaPulse/sql/advanced_analytics.sql#L15-L31)

---

### Finding 2: The Engagement Inversion Phenomenon (Reach vs. Interaction)
- **Business Question:** Does mass view volume translate to active viewer engagement across different genres?
- **SQL Technique:** Double CTE with `ROW_NUMBER() OVER(PARTITION BY category_title ORDER BY engagement_rate ASC)` and `COUNT(*) OVER(PARTITION BY category_title)` to extract the true 50th percentile (mathematical median) engagement rate without parametric distortion.
- **Actual Result (Q16):**
  - **Science & Technology:** **7.5610%** median engagement rate (301 unique videos)
  - **Education:** **5.6205%** median engagement rate (797 unique videos)
  - **Comedy:** **4.2236%** median engagement rate (1,116 unique videos)
  - **News & Politics:** **0.6609%** median engagement rate (2,506 unique videos)
  - **Entertainment:** **0.5823%** median engagement rate (7,557 unique videos)
- **Business Interpretation:** A pronounced inverse relationship exists between volume and engagement intensity. While Entertainment and News achieve massive passive reach, niche informational verticals generate **10x to 13x higher interaction rates**. Community-driven brands should sponsor educational and tech creators for high-intent conversion rather than mass-market broadcast channels.
- **Analytical Limitation:** Engagement rate measures interaction per observed view `((likes + comments) / views) * 100`; it cannot measure viewer retention, watch duration, or click-through rates.
- **Reference:** [Query 16 (sql/business_queries.sql)](file:///D:/MediaPulse/sql/business_queries.sql#L43-L73)

---

### Finding 3: Flagship Media Assets & Concentration of Viral Reach
- **Business Question:** What creative titles achieved the highest single-video cumulative reach, and how do they balance views versus engagement?
- **SQL Technique:** Grouped aggregation isolating `MAX(views)` per unique video joined with `channels` and `categories`, applying `NULLIF(views, 0)` for division safety.
- **Actual Result (Q02):**
  - **Rank 1:** *"YouTube Rewind: The Shape of 2017"* (YouTube Spotlight / Entertainment) — **125,432,237 views**, 2.91M likes, 827.7K comments (2.98% ER, 6 days trended).
  - **Rank 2:** *"Marvel Studios' Avengers: Infinity War Official Trailer"* (Marvel Entertainment / Entertainment) — **89,930,713 views**, 2.61M likes, 348.0K comments (3.29% ER, 8 days trended).
  - **Rank 3:** *"VENOM - Official Trailer (HD)"* (Sony Pictures Entertainment / Entertainment) — **53,822,757 views**, 1.25M likes, 135.4K comments (2.58% ER, 7 days trended).
  - **Rank 4:** *"Marvel Studios' Avengers: Infinity War - Official Trailer"* (Marvel Entertainment / Entertainment) — **45,064,699 views**, 1.49M likes, 186.0K comments (3.73% ER, 6 days trended).
  - **Rank 5:** *"Sanju | Official Teaser"* (FoxStarHindi / Entertainment) — **44,171,797 views**, 780.9K likes, 47.8K comments (1.88% ER, 9 days trended).
- **Business Interpretation:** Global entertainment franchises and marquee theatrical movie teasers capture extraordinary view volumes that outstrip standard episodic television by two orders of magnitude.
- **Analytical Limitation:** Cumulative view counts reflect global views on the video, not exclusively views originating from Indian IP addresses.
- **Reference:** [Query 02 (sql/advanced_analytics.sql)](file:///D:/MediaPulse/sql/advanced_analytics.sql#L33-L64)

---

### Finding 4: Rapid Trending Induction Window (48-Hour Velocity Rule)
- **Business Question:** How rapidly do published videos enter the YouTube India trending feed?
- **SQL Technique:** CTE calculating `DATEDIFF(MIN(trending_date), publish_date)` at the unique-video grain, grouped via `CASE WHEN` into operational latency brackets.
- **Actual Result (Q06):**
  - **Day 0 (Same Day):** 420 videos (**2.58%**)
  - **Day 1 – 2 (Rapid Induction):** 15,300 videos (**93.84%**)
  - **Cumulative within $\le 2$ Days:** **15,720 videos (96.41%)**
  - **Day 3 – 7 (Moderate Latency):** 565 videos (**3.47%**)
  - **Over 7 Days (Archival / Sleeper):** 20 videos (**0.12%**)
- **Business Interpretation:** YouTube's trending algorithm operates on extreme recency. Content that fails to gain immediate momentum within the first 48 hours of release has a negligible (3.59%) chance of ever entering the trending feed. Promotional spend and push notifications must be concentrated within the first 6–12 hours post-upload.
- **Analytical Limitation:** The dataset captures snapshots collected once daily; hourly induction precision is not recorded in the raw scrape.
- **Reference:** [Query 06 (sql/advanced_analytics.sql)](file:///D:/MediaPulse/sql/advanced_analytics.sql#L102-L127)

---

### Finding 5: Trending Shelf-Life & Transience (The 1-Day Horizon)
- **Business Question:** How long do trending videos sustain their presence on the leaderboard?
- **SQL Technique:** Grouped `COUNT(DISTINCT trending_date)` per unique video, aggregated into duration tiers.
- **Actual Result (Q07):**
  - **1 Day Only:** 7,824 unique videos (**47.99%**)
  - **2 Days:** 4,168 unique videos (**25.56%**)
  - **3 – 5 Days:** 4,087 unique videos (**25.07%**)
  - **Over 5 Days (High Longevity):** 226 unique videos (**1.39%**)
- **Business Interpretation:** Almost half (48%) of all trending videos appear for only a single snapshot observation, and 73.55% disappear within 2 days. The trending feed is highly volatile, functioning as a high-churn discovery mechanism rather than a durable archive.
- **Analytical Limitation:** Daily scraping gaps (such as missing dates in late April) may artificially truncate observed longitudinal runs for a minority of titles.
- **Reference:** [Query 07 (sql/advanced_analytics.sql)](file:///D:/MediaPulse/sql/advanced_analytics.sql#L129-L153)

---

### Finding 6: Publisher Portfolio Longevity & Publishing Concentration
- **Business Question:** Which media brands publish the highest volume of trending content, and how does their shelf life vary?
- **SQL Technique:** CTE aggregating video-level peak views and distinct trending days, joined with `channels`, sorted by `unique_videos DESC LIMIT 10`.
- **Actual Result (Q15):**
  - **Study IQ education:** 169 unique videos (32.8M cumulative peak views, 1.18 mean days trended)
  - **Tarang TV:** 158 unique videos (32.0M views, 1.26 mean days)
  - **VikatanTV:** 153 unique videos (71.3M views, 1.31 mean days)
  - **etvteluguindia:** 153 unique videos (118.9M views, 1.33 mean days)
  - **Saregama TVShows:** 152 unique videos (23.1M views, 1.17 mean days)
  - **Mazhavil Manorama:** 138 unique videos (41.2M views, 1.38 mean days)
  - **RadaanMedia:** 136 unique videos (56.1M views, 1.40 mean days)
  - **zeemarathi:** 135 unique videos (18.4M views, 1.21 mean days)
  - **zeetvtelugu:** 134 unique videos (23.4M views, 1.31 mean days)
  - **SAB TV:** 130 unique videos (47.7M views, 1.52 mean days)
- **Business Interpretation:** Top publishers are predominantly regional broadcast television networks and test-preparation educators maintaining high-frequency daily serial releases. While their individual video shelf life is brief (1.17 to 1.52 days), their massive catalog velocity ensures a permanent brand presence on the trending leaderboard.
- **Analytical Limitation:** Channels are identified by display title strings; independent creators who share exact channel names would be coalesced under the same surrogate key.
- **Reference:** [Query 15 (sql/business_queries.sql)](file:///D:/MediaPulse/sql/business_queries.sql#L15-L41)

---

### Finding 7: Month-Over-Month Trending Velocity Shifts
- **Business Question:** How did trending activity fluctuate across late 2017 and early 2018?
- **SQL Technique:** CTE grouping by `DATE_FORMAT(trending_date, '%Y-%m')`, applying window function `LAG()` to calculate absolute change and percentage growth with safe `NULLIF()` division.
- **Actual Result (Q11):**
  - **2017-11:** 3,158 snapshots (Baseline month; 17 active tracking days)
  - **2017-12:** 5,744 snapshots (+2,586 change, **+81.89%** MoM; 31 tracking days)
  - **2018-01:** 5,342 snapshots (-402 change, **-7.00%** MoM; 29 tracking days)
  - **2018-02:** 4,460 snapshots (-882 change, **-16.51%** MoM; 28 tracking days)
  - **2018-03:** 4,584 snapshots (+124 change, **+2.78%** MoM; 31 tracking days)
  - **2018-04:** 3,273 snapshots (-1,311 change, **-28.60%** MoM; 24 tracking days)
  - **2018-05:** 3,916 snapshots (+643 change, **+19.65%** MoM; 31 tracking days)
  - **2018-06:** 1,788 snapshots (-2,128 change, **-54.34%** MoM; 14 tracking days)
- **Business Interpretation:** Trending volume peaked in December 2017 and January 2018 during major holiday and theatrical release cycles. Sharp drops in April and June correlate directly with scraping outages and mid-month collection termination rather than genuine audience abandonment.
- **Analytical Limitation:** Variations in monthly tracking days (14 to 31 days) require normalizing by daily snapshot density (`avg_snapshots_per_day`) for fair longitudinal comparisons.
- **Reference:** [Query 11 (sql/window_functions.sql)](file:///D:/MediaPulse/sql/window_functions.sql#L66-L96)

---

### Finding 8: Optimal Upload Scheduling & Prime-Time ROI
- **Business Question:** What upload days and hours produce the highest publication density and viewing traction?
- **SQL Technique:** Custom day-of-week sorting using `FIELD()`, combined with mathematical hour transformation (`MOD(publish_hour + 5, 24)`) and window functions.
- **Actual Result (Q04, Q05, Q20):**
  - **Peak Upload Days:** Friday (**2,694 videos / 16.52%**) and Thursday (**2,502 videos / 15.34%**). Lowest on Sunday (**1,720 videos / 10.55%**).
  - **Prime-Time Upload Window (12:00–16:00 UTC / 17:30–21:30 IST):** 5,152 unique videos (31.60% of catalog), delivering **690.6K mean peak views** and **2.38% mean engagement rate**.
  - **Morning Window (04:00–08:00 UTC / 09:30–13:30 IST):** 4,473 unique videos (27.43% of catalog), delivering **750.5K mean peak views** and faster induction (**1.16 mean days to trend**).
- **Business Interpretation:** Digital publishers strategically schedule uploads for Thursday and Friday afternoons to capitalize on weekend entertainment consumption. However, morning uploads (09:30–13:30 IST) demonstrate 8.7% higher average peak views and 15% faster induction latency, suggesting an underserved morning commute / news consumption window.
- **Analytical Limitation:** Upload times reflect creator publishing choices, not necessarily consumer viewing peaks.
- **Reference:** [Query 04](file:///D:/MediaPulse/sql/advanced_analytics.sql#L66-L79), [Query 05](file:///D:/MediaPulse/sql/advanced_analytics.sql#L81-L100), [Query 20](file:///D:/MediaPulse/sql/business_queries.sql#L143-L175)

---

### Finding 9: Same-Day Viral Breakouts (Day-0 Velocity Premium)
- **Business Question:** Do videos that enter trending on the day of publication achieve superior view reach and engagement?
- **SQL Technique:** CTE isolating `MIN(trending_date) - publish_date = 0`, comparing aggregate mean views and engagement against standard induction videos.
- **Actual Result (Q17):**
  - **Same-Day Breakouts (Day 0):** 420 videos (**2.58%** share)
    - Mean Observed Peak Views: **725,977 views**
    - Mean Engagement Rate: **4.1146%**
  - **Standard Induction (Day 1+):** 15,885 videos (**97.42%** share)
    - Mean Observed Peak Views: **682,576 views**
    - Mean Engagement Rate: **2.0036%**
- **Business Interpretation:** Day-0 breakout videos represent a distinct high-velocity tier. They generate **6.4% higher average peak views** and **more than 2x the engagement intensity (4.11% vs. 2.00%)**. Achieving immediate algorithmic traction is a strong leading indicator of sustained viral performance.
- **Analytical Limitation:** Rapid induction may be driven by pre-existing creator subscriber bases rather than intrinsic video quality alone.
- **Reference:** [Query 17 (sql/business_queries.sql)](file:///D:/MediaPulse/sql/business_queries.sql#L75-L102)

---

### Finding 10: Audience Interaction Policies & Comment Disabling Penalties
- **Business Question:** How does disabling viewer comments impact video reach and engagement?
- **SQL Technique:** CTE grouping by `comments_disabled` boolean flag, calculating mean peak views, likes, comments, and engagement rates with safe division.
- **Actual Result (Q19):**
  - **Comments Enabled:** 15,732 videos (**96.49%**)
    - Mean Peak Views: **693,609 views**
    - Mean Peak Likes: **14,912 likes**
    - Mean Engagement Rate: **2.1125%**
  - **Comments Disabled:** 573 videos (**3.51%**)
    - Mean Peak Views: **411,453 views** (**40.7% lower**)
    - Mean Peak Likes: **2,099 likes** (**85.9% lower**)
    - Mean Engagement Rate: **0.5599%** (**73.5% lower**)
- **Business Interpretation:** Disabling audience commentary severely suppresses video performance. Videos with disabled comments experience a **40.7% reduction in mean peak views** and an **85.9% drop in likes**. Creators and brands should avoid disabling comments unless legally or reputationally mandatory, as the YouTube recommendation algorithm strongly disincentivizes non-interactive media.
- **Analytical Limitation:** Direction of causality cannot be definitively proven: controversial or low-quality videos may prompt creators to disable comments defensively after underperforming.
- **Reference:** [Query 19 (sql/business_queries.sql)](file:///D:/MediaPulse/sql/business_queries.sql#L119-L141)

---

## 4. Analytical Reconciliation: SQL vs. Pandas

To confirm that the relational SQL queries produce identical results to the Phase 4 Python exploratory analysis, all core aggregates were independently reconciled:

| Analytical Metric | MySQL 8 Query Result | Phase 4 Pandas KPI | Variance | Verification Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Catalog Unique Videos** | **16,305** | **16,305** | 0 | **100% RECONCILED** |
| **Entertainment Unique Videos** | **7,557** (46.35%) | **7,557** (46.35%) | 0 | **100% RECONCILED** |
| **News & Politics Unique Videos**| **2,506** (15.37%) | **2,506** (15.37%) | 0 | **100% RECONCILED** |
| **Science & Tech Median ER** | **7.5610%** | **7.5610%** | 0.0000% | **100% RECONCILED** |
| **Education Median ER** | **5.6205%** | **5.6205%** | 0.0000% | **100% RECONCILED** |
| **Comedy Median ER** | **4.2236%** | **4.2236%** | 0.0000% | **100% RECONCILED** |
| **Entertainment Median ER** | **0.5823%** | **0.5823%** | 0.0000% | **100% RECONCILED** |
| **Same-Day (Day 0) Latency** | **420 videos (2.58%)** | **420 videos (2.58%)** | 0 | **100% RECONCILED** |
| **Within 2 Days ($\le 2$d) Latency**| **15,720 videos (96.41%)** | **15,720 videos (96.41%)** | 0 | **100% RECONCILED** |
| **Top Channel Output (Study IQ)**| **169 unique videos** | **169 unique videos** | 0 | **100% RECONCILED** |

---

## 5. SQL Execution Performance & EXPLAIN Plan Analysis

Live MySQL `EXPLAIN` query plans were analyzed for representative complex queries:

### 1. Query 01 (Category Market Share):
- **Execution Plan:**
  - `table: c, type: index, key: uq_category_title, rows: 17, Extra: Using index; Using temporary`
  - `table: v, type: ref, key: idx_videos_category, rows: 960, Extra: Using index`
  - `table: <derived2>, type: ALL, rows: 16334, Extra: Using filesort`
- **Technical Insight:** The join between `categories` and `videos` utilizes covering secondary indexes (`idx_videos_category`), avoiding table row scans until window aggregation.

### 2. Query 09 (Top 3 Videos Per Category via `ROW_NUMBER()`):
- **Execution Plan:**
  - `table: s, type: ALL, rows: 27895, Extra: Using temporary; Using filesort`
  - `table: v, type: eq_ref, key: PRIMARY, rows: 1`
  - `table: cat, type: eq_ref, key: PRIMARY, rows: 1`
  - `table: <derived2>, type: ALL, rows: 27895, filtered: 33.33%, Extra: Using where; Using filesort`
- **Technical Insight:** `ROW_NUMBER() OVER(PARTITION BY category_id ORDER BY peak_views DESC)` sorts partitioned partitions efficiently; the primary key lookups (`eq_ref`) for `v` and `cat` resolve in $O(1)$ constant time.

### 3. Query 12 (Rolling 7-Day Window Framing):
- **Execution Plan:**
  - `table: trending_snapshots, type: ALL, rows: 27895, Extra: Using temporary; Using filesort`
  - `table: <derived2>, type: ALL, rows: 27895, Extra: None`
- **Technical Insight:** The window frame `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` executes sequentially across the 205 pre-aggregated daily records, completing in 0.115s.

---

## 6. Automated Test Suite Results

The comprehensive test suite incorporates unit tests, operational checks, and live SQL assertions:

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- D:\MediaPulse\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\MediaPulse
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.14.5
collected 67 items

tests/test_cleaning.py ..............                                    [ 20%]
tests/test_database.py .....                                             [ 28%]
tests/test_eda.py ...........                                            [ 44%]
tests/test_ingestion.py .....                                            [ 52%]
tests/test_metrics.py .........                                          [ 65%]
tests/test_profiling.py ..........                                       [ 80%]
tests/test_smoke.py ....                                                 [ 86%]
tests/test_sql_analytics.py .........                                    [100%]

======================== 67 passed in 79.24s (0:01:19) ========================
```
- **67 Tests Passed / 0 Failed / 0 Skipped / 0 Warnings:** Validates query execution, non-empty datasets, column contracts, window rankings, month-over-month lag values, rolling moving averages, and exact mathematical reconciliation against Phase 4 KPIs.

---

## 7. Deliverables Summary

1. [advanced_analytics.sql](file:///D:/MediaPulse/sql/advanced_analytics.sql): Core analytical queries (Q01–Q08).
2. [window_functions.sql](file:///D:/MediaPulse/sql/window_functions.sql): Advanced window and ranking queries (Q09–Q14).
3. [business_queries.sql](file:///D:/MediaPulse/sql/business_queries.sql): Strategic business intelligence queries (Q15–Q20).
4. [test_sql_analytics.py](file:///D:/MediaPulse/tests/test_sql_analytics.py): 9 automated SQL integration tests.
5. [sql_analytics_report.md](file:///D:/MediaPulse/reports/sql_analytics_report.md): In-depth analytical and performance report.
6. [sql_query_explanations.md](file:///D:/MediaPulse/reports/sql_query_explanations.md): Technical explanations and 15 SQL interview questions & answers.
