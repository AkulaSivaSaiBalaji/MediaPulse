# MediaPulse — SQL Technical Guide & Interview Preparation Manual

**Project:** MediaPulse — Media Performance & Audience Analytics  
**Target Role:** Wipro Analyst L1 (Job ID: 218535) — Business Analyst / Data Analyst (Media)  
**Database Reference:** MySQL Server 8.0+ (`mediapulse_db`)  
**Scope:** Technical Concept Explanations & 15 Real-World SQL Interview Q&A  

---

## Part 1: Core SQL Concepts Explained for Media Analytics

### 1. Why SQL Queries Are Needed in Media Analytics
In production media organizations (such as Disney+ Hotstar, Zee, SonyLIV, or YouTube creator networks), raw tracking data is generated continuously by video players and content scrapers. Flat CSV files and Excel spreadsheets quickly fail under scale, concurrency, and integrity requirements.
- **Data Integrity & Consistency:** Relational databases enforce constraints (foreign keys, uniqueness) preventing corrupt or orphan records.
- **High-Velocity Aggregation:** SQL engines process millions of rows in sub-seconds using multi-threaded B-tree index scans.
- **Single Source of Truth:** SQL establishes standardized business logic (e.g., how engagement rate is calculated, how duplicates are resolved), ensuring all business analysts and dashboards report identical metrics.

---

### 2. How Multi-Table JOINs Work (INNER JOIN vs. LEFT JOIN)
In MediaPulse, content attributes are normalized across tables: `categories`, `channels`, `videos`, and `trending_snapshots`. To analyze media performance, we must recombine them:

- **INNER JOIN:**
  - *Mechanism:* Evaluates join predicates (`ON tableA.key = tableB.key`) and returns rows only when a matching key exists in **both** tables.
  - *Media Example:* Joining `videos v INNER JOIN channels ch ON v.channel_id = ch.channel_id`. If a video has an invalid or missing `channel_id`, it is excluded from the result set.
- **LEFT JOIN (LEFT OUTER JOIN):**
  - *Mechanism:* Returns **all** rows from the left table, matching rows from the right table where possible, and populating `NULL` for right-table columns when no match exists.
  - *Orphan Audit Example:* 
    ```sql
    SELECT COUNT(*) FROM videos v
    LEFT JOIN channels c ON v.channel_id = c.channel_id
    WHERE c.channel_id IS NULL;
    ```
    If this query returns `0`, it guarantees that zero orphan videos exist in the catalog.

---

### 3. Why Common Table Expressions (CTEs) Are Preferred Over Nested Subqueries
A Common Table Expression (`WITH cte_name AS (...)`) defines a temporary named result set within the execution scope of a single SQL statement.

#### Comparison: CTE vs. Nested Subquery
```sql
-- Nested Subquery Approach (Difficult to read, hard to debug)
SELECT category_title, unique_videos
FROM (
    SELECT c.category_title, COUNT(v.video_id) AS unique_videos
    FROM categories c JOIN videos v ON c.category_id = v.category_id
    GROUP BY c.category_title
) sub
WHERE unique_videos > 100;

-- CTE Approach (Modular, readable, reusable)
WITH category_summary AS (
    SELECT c.category_title, COUNT(v.video_id) AS unique_videos
    FROM categories c JOIN videos v ON c.category_id = v.category_id
    GROUP BY c.category_title
)
SELECT category_title, unique_videos
FROM category_summary
WHERE unique_videos > 100;
```

#### Strategic Advantages of CTEs:
1. **Top-to-Bottom Readability:** Follows logical data transformation order (extract $ightarrow$ aggregate $ightarrow$ filter).
2. **Reusability:** A single CTE can be referenced multiple times in the main query (e.g., self-joins or comparisons against overall averages).
3. **Multi-Stage Pipelines:** Enables chaining multiple CTEs (`WITH cte1 AS (...), cte2 AS (...)`) to modularize complex business logic.

---

### 4. Differences Between ROW_NUMBER(), RANK(), and DENSE_RANK()
When ranking media assets or channels, handling ties (identical metric values) is critical.

| Window Function | Tie Handling Behavior | Numbering Sequence After Tie | Best Media Use Case |
| :--- | :--- | :--- | :--- |
| **`ROW_NUMBER()`** | Assigns distinct consecutive integers; arbitrarily breaks ties unless secondary sorting is specified. | `1, 2, 3, 4, 5...` | Selecting strictly the **Top $N$ items** (e.g., Top 3 videos per category in Q09). |
| **`RANK()`** | Assigns identical rank to ties; skips subsequent ranks equal to tie count. | `1, 2, 2, 4, 5...` (Skips rank 3) | Traditional competition ranking (Olympics style). |
| **`DENSE_RANK()`** | Assigns identical rank to ties; does **not** skip subsequent ranks. | `1, 2, 2, 3, 4...` (No rank skipped) | Tiered channel output ranking (e.g., Channel ranking within category in Q10). |

#### Visual Comparison Example:
Imagine three channels produce 10, 8, 8, and 5 trending videos:
- `ROW_NUMBER()`: Channel A = 1, Channel B = 2, Channel C = 3, Channel D = 4
- `RANK()`: Channel A = 1, Channel B = 2, Channel C = 2, Channel D = **4** (Rank 3 skipped)
- `DENSE_RANK()`: Channel A = 1, Channel B = 2, Channel C = 2, Channel D = **3** (Rank 3 preserved)

---

### 5. How Window Functions Differ Fundamentally from GROUP BY
This is one of the most frequently asked questions in data analyst interviews.

- **`GROUP BY` (Collapsing Aggregation):**
  - Collapses multiple rows into a single summary row per group.
  - You lose individual row details; you can only query grouped columns and aggregate functions (`SUM`, `AVG`, `COUNT`).
  - *Example:* If 16,305 videos are grouped by 17 categories, `GROUP BY` returns exactly 17 rows.
- **Window Functions (`OVER()`) (Non-Collapsing Calculation):**
  - Performs calculations across a set of table rows related to the current row, but **preserves individual row identity**.
  - Returns the exact same number of rows as the input dataset.
  - *Example:* You can display each video's title, its views, and alongside it display the total views of its entire category using `SUM(views) OVER(PARTITION BY category_id)`.

#### Direct Visual Comparison:
```sql
-- GROUP BY collapses to 17 rows:
SELECT category_id, COUNT(*) AS video_count FROM videos GROUP BY category_id;

-- Window Function preserves all 16,305 rows while appending category totals:
SELECT video_id, category_id, COUNT(*) OVER(PARTITION BY category_id) AS total_in_category FROM videos;
```

---

### 6. Why Duplicate Daily Snapshot Observations Distort Cumulative Metrics
In longitudinal trending datasets, a video trending for 5 consecutive days generates **5 separate snapshot rows**. Each row records cumulative view counts on that calendar day (e.g., Day 1: 100K, Day 2: 150K, Day 3: 180K, Day 4: 200K, Day 5: 210K).

- **The Pitfall:** If an analyst runs `SUM(views)` across all rows, the result is:
  $$100K + 150K + 180K + 200K + 210K = 840,000 	ext{ views}$$
  This inflates the video's actual reach by **4x**!
- **The Solution:** The true observed peak views for that video is:
  $$	ext{MAX}(	ext{views}) = 210,000 	ext{ views}$$
- **MediaPulse Analytical Rule:** Always rollup snapshots to the unique `video_id` grain using `MAX(views)` before performing category or channel-level view aggregations.

---

### 7. How MySQL Indexes Improve Query Execution Plans
Without indexes, MySQL must perform a **Full Table Scan (`ALL`)**, reading every single page from disk into memory to evaluate a `WHERE` clause.
- **B-Tree Structure:** A B-tree index stores indexed column values in a balanced sorted tree structure, reducing the search space significantly compared to reading every data page sequentially.
- **Index Equality Lookups (`eq_ref` / `ref`):**
  - An `eq_ref` join lookup matches a single row from a unique or primary index, avoiding full-table scans. However, it should not be described as $O(1)$ constant time; actual cost involves B-tree page traversals based on tree depth and buffer pool cache hits.
  - `idx_snapshots_trending_date` on `trending_snapshots(trending_date)`: Allows isolating the 128 snapshots for a given date in **3 milliseconds** instead of scanning 32,265 rows.
  - `idx_snapshots_views` on `trending_snapshots(views DESC)`: Allows MySQL to satisfy `ORDER BY views DESC LIMIT 10` by reading the pre-sorted index leaf nodes directly, completely eliminating expensive in-memory **filesort** operations.

---

## Part 2: 15 Real-World SQL Interview Questions & Answers

### Q1: In the MediaPulse project, why did you create a surrogate primary key for `channels` instead of using `channel_title` as the natural key?
**Answer:**  
In the raw Kaggle YouTube dataset, YouTube's authoritative 24-character alphanumeric Channel ID (e.g., `UC...`) was absent, leaving only `channel_title` strings. While natural keys are conceptually simple, string keys have significant drawbacks:
1. `channel_title VARCHAR(255)` consumes up to 255 bytes per foreign key reference in child tables (`videos`), creating bloated secondary indexes. An `INT AUTO_INCREMENT` surrogate key consumes only 4 bytes, dramatically reducing memory and disk footprint.
2. Channel titles can theoretically be renamed by publishers; using an immutable surrogate key insulates child records from cascading update anomalies.
3. Case-sensitivity nuances (e.g., `'Zee TV'` vs. `'Zee Tv'`) required binary collation (`utf8mb4_bin`) to ensure unique identity without dropping distinct publishers.

---

### Q2: How did you calculate each category's percentage share of total unique videos without running two separate queries?
**Answer:**  
I combined a Common Table Expression with a window function `SUM() OVER()`:
```sql
WITH category_counts AS (
    SELECT c.category_title, COUNT(v.video_id) AS unique_videos
    FROM categories c JOIN videos v ON c.category_id = v.category_id
    GROUP BY c.category_title
)
SELECT 
    category_title,
    unique_videos,
    ROUND(unique_videos * 100.0 / SUM(unique_videos) OVER(), 2) AS catalog_share_pct
FROM category_counts
ORDER BY unique_videos DESC;
```
`SUM(unique_videos) OVER()` computes the grand total across all rows (16,305) in a single pass, allowing inline percentage calculation without a subquery or join back to a summary table.

---

### Q3: Explain how you calculated the mathematical median engagement rate in MySQL 8, given that MySQL has no built-in `MEDIAN()` function.
**Answer:**  
I implemented an exact percentile calculation using window functions:
```sql
WITH video_engagement AS (
    SELECT 
        v.video_id, cat.category_title,
        ROUND((MAX(s.likes) + MAX(s.comment_count)) * 100.0 / NULLIF(MAX(s.views), 0), 4) AS engagement_rate
    FROM videos v
    JOIN categories cat ON v.category_id = cat.category_id
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, cat.category_title
),
ranked_engagement AS (
    SELECT 
        category_title, engagement_rate,
        ROW_NUMBER() OVER(PARTITION BY category_title ORDER BY engagement_rate ASC, video_id ASC) AS row_asc,
        COUNT(*) OVER(PARTITION BY category_title) AS total_count
    FROM video_engagement
)
SELECT 
    category_title,
    ROUND(AVG(engagement_rate), 4) AS median_engagement_rate
FROM ranked_engagement
WHERE row_asc IN (FLOOR((total_count + 1) / 2.0), CEIL((total_count + 1) / 2.0))
GROUP BY category_title;
```
For odd count $N$, `FLOOR` and `CEIL` resolve to the exact middle row $((N+1)/2)$. For even count $N$, they resolve to rows $N/2$ and $N/2 + 1$, and `AVG()` averages both, satisfying the formal mathematical definition of median.

---

### Q4: What is the difference between `NULLIF()` and `COALESCE()`, and where did you apply `NULLIF()` in this project?
**Answer:**  
- `COALESCE(val1, val2, ...)` returns the first non-null argument in the list. It is commonly used to provide default fallbacks for missing values (e.g., `COALESCE(description, 'No description provided')`).
- `NULLIF(expr1, expr2)` returns `NULL` if `expr1 = expr2`; otherwise it returns `expr1`.
In MediaPulse, `NULLIF()` was applied to prevent **division-by-zero errors** during rate calculations:
$$	ext{ROUND}((	ext{likes} + 	ext{comments}) * 100.0 / 	ext{NULLIF}(	ext{views}, 0), 4)$$
If a video has 0 views, `NULLIF(views, 0)` returns `NULL`, which evaluates the entire division to `NULL` rather than crashing the query with a fatal runtime error.

---

### Q5: How did you isolate the top 3 videos per category by observed views? Why not use `LIMIT 3`?
**Answer:**  
`LIMIT 3` restricts the entire query result to 3 rows overall. To get 3 rows **per category** across all 17 categories (up to 51 rows), a window ranking function partitioned by category is required:
```sql
WITH ranked_videos AS (
    SELECT 
        v.video_id, v.title, cat.category_title, MAX(s.views) AS peak_views,
        ROW_NUMBER() OVER(
            PARTITION BY v.category_id 
            ORDER BY MAX(s.views) DESC, v.video_id ASC
        ) AS rank_in_category
    FROM videos v
    JOIN categories cat ON v.category_id = cat.category_id
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.title, cat.category_title, v.category_id
)
SELECT category_title, rank_in_category, title, peak_views
FROM ranked_videos
WHERE rank_in_category <= 3
ORDER BY category_title ASC, rank_in_category ASC;
```

---

### Q6: How do you calculate Month-over-Month (MoM) growth in SQL?
**Answer:**  
Using the `LAG()` window function to retrieve the prior month's observation metric:
```sql
WITH monthly_metrics AS (
    SELECT 
        DATE_FORMAT(trending_date, '%Y-%m') AS trending_year_month,
        COUNT(*) AS total_snapshots
    FROM trending_snapshots
    GROUP BY DATE_FORMAT(trending_date, '%Y-%m')
)
SELECT 
    trending_year_month,
    total_snapshots,
    LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC) AS prior_month_snapshots,
    ROUND(
        (total_snapshots - LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC)) * 100.0 /
        NULLIF(LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC), 0),
        2
    ) AS mom_growth_pct
FROM monthly_metrics;
```
`LAG(column, offset)` accesses the row preceding the current row based on chronological order. On the very first row, `LAG()` returns `NULL`, which `NULLIF()` safely protects.

---

### Q7: What is the difference between a row-based frame (`ROWS BETWEEN`) and a calendar-based frame (`RANGE BETWEEN`), and which was used in Query 12?
**Answer:**  
- `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` defines a frame based on a physical count of rows (the current row plus the 6 rows before it in sorted order).
- `RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW` defines a logical calendar frame based on values (dates within the last 6 calendar days).
In Query 12, the historical dataset contains 205 distinct observed snapshot dates across a 213-calendar-day span, meaning 8 calendar dates are unobserved due to scraping collection outages. Because the time series has date gaps, `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` functions strictly as a **7-observation rolling window** (smoothing the current observed date and the 6 preceding observed dates), rather than an uninterrupted 7-calendar-day window.

---

### Q8: What is the difference between `WHERE` and `HAVING`?
**Answer:**  
- `WHERE` filters individual rows **before** any grouping or aggregation takes place. It cannot evaluate aggregate functions (e.g., `WHERE COUNT(*) > 5` is invalid SQL).
- `HAVING` filters aggregated groups **after** `GROUP BY` has collapsed rows.
*MediaPulse Example:* In duplicate detection, `HAVING COUNT(*) > 1` finds `(video_id, trending_date)` groups with more than one row.

---

### Q9: Why did `YEAR_MONTH` throw a syntax error in your MySQL queries, and how did you resolve it?
**Answer:**  
In MySQL 8, `YEAR_MONTH` is a **reserved keyword** used for interval expressions (e.g., `INTERVAL 1 YEAR_MONTH` in date arithmetic). When used as an unquoted column alias (`AS year_month`), the SQL parser expects an interval specification and fails with syntax error 1064.
We resolved this by either:
1. Enclosing the identifier in backticks: ``AS `year_month` ``.
2. Renaming the alias to a descriptive non-reserved business identifier: `AS trending_year_month`. We adopted `trending_year_month` across our SQL codebase for clarity and portability.

---

### Q10: Why did you use `CHARACTER SET utf8mb4 COLLATE utf8mb4_bin` for channel titles?
**Answer:**  
The dataset contained 1,423 distinct channel titles, including case-variant titles:
- `'ABP Majha'` vs. `'Abp Majha'`
- `'Zee TV'` vs. `'Zee Tv'`
Under MySQL's default case-insensitive collation (`utf8mb4_unicode_ci`), MySQL treats `'Zee TV'` and `'Zee Tv'` as identical duplicates. This collapsed channels from 1,423 to 1,421 and broke foreign key references during video ingestion. By setting binary collation (`utf8mb4_bin`), comparison is based on byte-level UTF-8 code points, preserving exact case distinctions and ensuring 100% video-to-channel mapping.

---

### Q11: How do you calculate a Pareto 80/20 cumulative distribution in SQL?
**Answer:**  
Using `SUM() OVER(ORDER BY ... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` to generate running cumulative view totals divided by grand total views:
```sql
SELECT 
    category_title,
    category_observed_peak_views,
    ROUND(
        SUM(category_observed_peak_views) OVER(
            ORDER BY category_observed_peak_views DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) * 100.0 / SUM(category_observed_peak_views) OVER(),
        2
    ) AS cumulative_peak_views_pct
FROM category_peaks;
```
This revealed that Entertainment and Music alone account for **60.99%** of all observed peak views, and the top 5 categories capture **83.29%**.

---

### Q12: How would you optimize a query that is performing a slow `Using filesort` on `ORDER BY views DESC LIMIT 50`?
**Answer:**  
A `Using filesort` indicates that MySQL must retrieve rows into a temporary buffer and perform a quicksort algorithm in memory or disk.
To optimize:
1. Create a descending B-tree index on the sorted column: `CREATE INDEX idx_snapshots_views ON trending_snapshots(views DESC);`.
2. MySQL can then read the first 50 index leaf nodes in order and stop immediately, reducing execution time from hundreds of milliseconds to under 1 millisecond.

---

### Q13: In your schema, why are mutable flags like `comments_disabled` stored in both `videos` and `trending_snapshots`?
**Answer:**  
This reflects the dimensional modeling principle of separating **canonical asset metadata** from **point-in-time observational facts**:
- 24 videos in the dataset had comments disabled by creators *after* trending.
- If `comments_disabled` were stored only on `videos`, updating it would overwrite historical reality: on Day 1 when comments were open, engagement was measurable, but on Day 3 comments were turned off.
- Storing the flag in `trending_snapshots` preserves historical accuracy for time-series audits, while storing it in `videos` records the status at initial publication.

---

### Q14: How does `FIELD()` function work in MySQL, and where was it applied?
**Answer:**  
`FIELD(str, str1, str2, str3, ...)` returns the 1-based index position of `str` within the argument list.
In Query 04, publication weekdays (`publish_day_name`) are string values (`'Monday'`, `'Tuesday'`, etc.). Standard `ORDER BY publish_day_name` sorts alphabetically (`Friday`, `Monday`, `Saturday`...), which is chronologically nonsensical.
Using:
```sql
ORDER BY FIELD(publish_day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday');
```
forces MySQL to order the output in true calendar week sequence.

---

### Q15: How do you verify that an analytical SQL query does not suffer from Cartesian join multiplication?
**Answer:**  
Cartesian multiplication occurs when a table with a 1-to-many relationship is joined with another table that also has a 1-to-many relationship, multiplying row counts exponentially.
To verify and prevent this:
1. **Pre-Aggregate in CTEs:** Always aggregate child tables down to their parent primary key (e.g., rolling up snapshots to `video_id` peak metrics) *before* joining to channels or categories.
2. **Row Count Audit:** Verify that `COUNT(DISTINCT video_id)` equals `COUNT(v.video_id)`. If `COUNT(*)` exceeds unique videos, an unintended Cartesian fan-out occurred.
3. **EXPLAIN Review:** Check the `rows` estimation in `EXPLAIN`. If row estimates explode beyond the table dimensions, join conditions must be tightened.
