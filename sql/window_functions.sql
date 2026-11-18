-- ==============================================================================
-- MediaPulse — Phase 6: Advanced SQL Analytics
-- File: sql/window_functions.sql
-- Description: Advanced analytical window functions, ranking algorithms,
--              month-over-month lag comparisons, rolling averages, and
--              partitioned category contributions.
-- Target Database: MySQL Server 8.0+ (mediapulse_db)
-- Analytical Rules:
--   1. Enforces deterministic tie-breaking in ROW_NUMBER() and DENSE_RANK().
--   2. Safe division using NULLIF(denominator, 0).
--   3. Moving frame specifications explicit via ROWS BETWEEN.
-- ==============================================================================

USE mediapulse_db;

-- ------------------------------------------------------------------------------
-- Query 09: Top 3 Videos Per Category by Peak Views
-- Concept: CTE, ROW_NUMBER() OVER(PARTITION BY category_id ORDER BY peak_views DESC)
-- Business Purpose: Identifies the top three flagship creative assets for every
--                   genre, isolating category leaders for media programming benchmarks.
-- ------------------------------------------------------------------------------
WITH ranked_category_videos AS (
    SELECT
        v.video_id,
        v.title,
        ch.channel_title,
        cat.category_title,
        MAX(s.views) AS peak_views,
        ROW_NUMBER() OVER(
            PARTITION BY v.category_id
            ORDER BY MAX(s.views) DESC, v.video_id ASC
        ) AS rank_in_category
    FROM videos v
    JOIN channels ch ON v.channel_id = ch.channel_id
    JOIN categories cat ON v.category_id = cat.category_id
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.title, ch.channel_title, cat.category_title, v.category_id
)
SELECT
    category_title,
    rank_in_category,
    video_id,
    title,
    channel_title,
    peak_views
FROM ranked_category_videos
WHERE rank_in_category <= 3
ORDER BY category_title ASC, rank_in_category ASC;

-- ------------------------------------------------------------------------------
-- Query 10: Channel Ranking Within Each Category Using DENSE_RANK()
-- Concept: CTE, DENSE_RANK() OVER(PARTITION BY category_title ORDER BY unique_videos DESC)
-- Business Purpose: Ranks media publishers within their respective genres based on
--                   catalog output, properly handling ties without skipping rank numbers.
-- ------------------------------------------------------------------------------
WITH channel_category_counts AS (
    SELECT
        c.category_title,
        ch.channel_title,
        COUNT(DISTINCT v.video_id) AS unique_videos
    FROM videos v
    JOIN channels ch ON v.channel_id = ch.channel_id
    JOIN categories c ON v.category_id = c.category_id
    GROUP BY c.category_title, ch.channel_title
)
SELECT
    category_title,
    channel_title,
    unique_videos,
    DENSE_RANK() OVER(
        PARTITION BY category_title
        ORDER BY unique_videos DESC, channel_title ASC
    ) AS channel_dense_rank
FROM channel_category_counts
ORDER BY category_title ASC, channel_dense_rank ASC;

-- ------------------------------------------------------------------------------
-- Query 11: Month-over-Month Trending Activity Growth Using LAG()
-- Concept: CTE, DATE_FORMAT(), LAG() OVER(), Safe Null Division
-- Business Purpose: Calculates month-over-month (MoM) growth rates in snapshot
--                   observations and unique video additions, highlighting velocity shifts.
-- ------------------------------------------------------------------------------
WITH monthly_observations AS (
    SELECT
        DATE_FORMAT(trending_date, '%Y-%m') AS trending_year_month,
        COUNT(*) AS total_snapshots,
        COUNT(DISTINCT video_id) AS unique_videos
    FROM trending_snapshots
    GROUP BY DATE_FORMAT(trending_date, '%Y-%m')
)
SELECT
    trending_year_month,
    total_snapshots,
    LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC) AS prior_month_snapshots,
    total_snapshots - LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC) AS snapshot_net_change,
    ROUND(
        (total_snapshots - LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC)) * 100.0 /
        NULLIF(LAG(total_snapshots, 1) OVER(ORDER BY trending_year_month ASC), 0),
        2
    ) AS mom_growth_pct,
    unique_videos,
    LAG(unique_videos, 1) OVER(ORDER BY trending_year_month ASC) AS prior_month_unique_videos
FROM monthly_observations
ORDER BY trending_year_month ASC;

-- ------------------------------------------------------------------------------
-- Query 12: Rolling 7-Observation Trending Snapshots (Window Frame Analysis)
-- Concept: CTE, Window Frame (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), Moving Averages
-- Analytical Note: Evaluates a 7-observation sliding window across the 205 distinct
--                  observed snapshot dates (which contain 8 collection gaps across the
--                  213-calendar-day historical span), rather than a continuous 7-calendar-day window.
-- ------------------------------------------------------------------------------
WITH daily_snapshot_counts AS (
    SELECT
        trending_date,
        COUNT(*) AS daily_snapshots,
        COUNT(DISTINCT video_id) AS daily_unique_videos
    FROM trending_snapshots
    GROUP BY trending_date
)
SELECT
    trending_date,
    daily_snapshots,
    daily_unique_videos,
    SUM(daily_snapshots) OVER(
        ORDER BY trending_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7obs_total_snapshots,
    ROUND(
        AVG(daily_snapshots) OVER(
            ORDER BY trending_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_7obs_avg_snapshots
FROM daily_snapshot_counts
ORDER BY trending_date ASC;

-- ------------------------------------------------------------------------------
-- Query 13: Category Contribution to Cumulative Observed Peak Views
-- Concept: CTE, Window SUM() OVER(), Running Total with UNBOUNDED PRECEDING
-- Business Purpose: Calculates Pareto distribution of audience attention, quantifying
--                   the percentage of total catalog views captured by each genre.
-- ------------------------------------------------------------------------------
WITH category_peaks AS (
    SELECT
        c.category_id,
        c.category_title,
        SUM(vp.peak_views) AS category_observed_peak_views
    FROM (
        SELECT video_id, category_id, MAX(views) AS peak_views
        FROM videos v
        JOIN trending_snapshots s USING (video_id)
        GROUP BY video_id, category_id
    ) vp
    JOIN categories c ON vp.category_id = c.category_id
    GROUP BY c.category_id, c.category_title
)
SELECT
    category_title,
    category_observed_peak_views,
    SUM(category_observed_peak_views) OVER() AS total_catalog_peak_views,
    ROUND(
        category_observed_peak_views * 100.0 / SUM(category_observed_peak_views) OVER(),
        2
    ) AS share_of_peak_views_pct,
    ROUND(
        SUM(category_observed_peak_views) OVER(
            ORDER BY category_observed_peak_views DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) * 100.0 / SUM(category_observed_peak_views) OVER(),
        2
    ) AS cumulative_peak_views_pct
FROM category_peaks
ORDER BY category_observed_peak_views DESC;

-- ------------------------------------------------------------------------------
-- Query 14: Channel Share of Category Peak Views Using SUM() OVER(PARTITION BY)
-- Concept: CTE, Window SUM() OVER(PARTITION BY category_title), Market Share Ranking
-- Business Purpose: Determines channel dominance within specific genres, identifying
--                   which categories are monopolized by major publishers vs fragmented.
-- ------------------------------------------------------------------------------
WITH channel_category_peaks AS (
    SELECT
        v.category_id,
        c.category_title,
        ch.channel_title,
        COUNT(DISTINCT v.video_id) AS channel_category_videos,
        SUM(vp.peak_views) AS channel_category_peak_views
    FROM (
        SELECT video_id, MAX(views) AS peak_views
        FROM trending_snapshots
        GROUP BY video_id
    ) vp
    JOIN videos v ON vp.video_id = v.video_id
    JOIN categories c ON v.category_id = c.category_id
    JOIN channels ch ON v.channel_id = ch.channel_id
    GROUP BY v.category_id, c.category_title, ch.channel_title
)
SELECT
    category_title,
    channel_title,
    channel_category_videos,
    channel_category_peak_views,
    SUM(channel_category_peak_views) OVER(PARTITION BY category_title) AS total_category_peak_views,
    ROUND(
        channel_category_peak_views * 100.0 /
        NULLIF(SUM(channel_category_peak_views) OVER(PARTITION BY category_title), 0),
        2
    ) AS channel_view_share_within_category_pct
FROM channel_category_peaks
ORDER BY category_title ASC, channel_category_peak_views DESC;
