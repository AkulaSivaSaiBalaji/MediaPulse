-- ==============================================================================
-- MediaPulse — Phase 6: Advanced SQL Analytics
-- File: sql/advanced_analytics.sql
-- Description: Core aggregations, dimensional distributions, time-to-trend
--              latency, longitudinal persistence, and audience engagement tiers.
-- Target Database: MySQL Server 8.0+ (mediapulse_db)
-- Analytical Rules:
--   1. Video-level grain rolls up snapshots via MAX(views), MIN(trending_date).
--   2. Prevents double-counting cumulative daily snapshot views.
--   3. Safe division enforced using NULLIF(denominator, 0).
-- ==============================================================================

USE mediapulse_db;

-- ------------------------------------------------------------------------------
-- Query 01: Top Categories by Unique Video Count and Percentage Share
-- Concept: Common Table Expression (CTE), COUNT(), Window SUM() OVER()
-- Business Purpose: Identifies content volume concentration and category market
--                   share across the entire Indian trending surface.
-- ------------------------------------------------------------------------------
WITH category_counts AS (
    SELECT
        c.category_id,
        c.category_title,
        COUNT(v.video_id) AS unique_videos
    FROM categories c
    JOIN videos v ON c.category_id = v.category_id
    GROUP BY c.category_id, c.category_title
)
SELECT
    category_id,
    category_title,
    unique_videos,
    ROUND(unique_videos * 100.0 / SUM(unique_videos) OVER(), 2) AS catalog_share_pct
FROM category_counts
ORDER BY unique_videos DESC;

-- ------------------------------------------------------------------------------
-- Query 02: Top 10 Videos by Maximum Observed Cumulative Views
-- Concept: CTE, Multi-Table JOIN (videos, channels, categories), NULLIF() Safe Division
-- Business Purpose: Isolates breakout media assets by maximum observed reach,
--                   reporting final cumulative views, likes, and engagement rate.
-- ------------------------------------------------------------------------------
WITH video_peaks AS (
    SELECT
        video_id,
        MAX(views) AS peak_views,
        MAX(likes) AS peak_likes,
        MAX(dislikes) AS peak_dislikes,
        MAX(comment_count) AS peak_comments,
        COUNT(DISTINCT trending_date) AS days_trended
    FROM trending_snapshots
    GROUP BY video_id
)
SELECT
    v.video_id,
    v.title,
    ch.channel_title,
    cat.category_title,
    vp.peak_views,
    vp.peak_likes,
    vp.peak_comments,
    vp.days_trended,
    ROUND((vp.peak_likes + vp.peak_comments) * 100.0 / NULLIF(vp.peak_views, 0), 4) AS peak_engagement_rate
FROM video_peaks vp
JOIN videos v ON vp.video_id = v.video_id
JOIN channels ch ON v.channel_id = ch.channel_id
JOIN categories cat ON v.category_id = cat.category_id
ORDER BY vp.peak_views DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- Query 03: Monthly Trending Activity Time-Series
-- Concept: DATE_FORMAT(), Aggregate Metrics, Longitudinal Tracking
-- Business Purpose: Tracks seasonal changes in trending volume, measuring snapshot
--                   density and distinct creative assets per calendar month.
-- ------------------------------------------------------------------------------
SELECT
    DATE_FORMAT(trending_date, '%Y-%m') AS trending_year_month,
    COUNT(*) AS total_snapshot_observations,
    COUNT(DISTINCT video_id) AS unique_trending_videos,
    COUNT(DISTINCT trending_date) AS active_tracking_days,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT trending_date), 2) AS avg_snapshots_per_day
FROM trending_snapshots
GROUP BY DATE_FORMAT(trending_date, '%Y-%m')
ORDER BY trending_year_month ASC;

-- ------------------------------------------------------------------------------
-- Query 04: Publication Weekday Upload Distribution
-- Concept: GROUP BY, Window SUM() OVER(), Custom Sorting with FIELD()
-- Business Purpose: Analyzes day-of-week release scheduling patterns to identify
--                   peak upload days for digital content creators.
-- ------------------------------------------------------------------------------
SELECT
    publish_day_name,
    COUNT(*) AS unique_videos_published,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS publication_share_pct
FROM videos
GROUP BY publish_day_name
ORDER BY FIELD(publish_day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday');

-- ------------------------------------------------------------------------------
-- Query 05: Publication Hour Distribution (UTC and Local IST Alignment)
-- Concept: GROUP BY, Mathematical Offset (MOD for IST), Window Function
-- Business Purpose: Identifies prime-time publishing windows across the 24-hour cycle,
--                   mapping UTC timestamps to Indian Standard Time (IST = UTC + 5:30).
-- ------------------------------------------------------------------------------
SELECT
    publish_hour AS publish_hour_utc,
    MOD(publish_hour + 5, 24) AS publish_hour_approx_ist,
    COUNT(*) AS unique_videos_published,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS upload_share_pct
FROM videos
GROUP BY publish_hour
ORDER BY publish_hour ASC;

-- ------------------------------------------------------------------------------
-- Query 06: Time to First Observed Trending Appearance (Unique-Video Latency)
-- Concept: CTE, MIN(trending_date), DATEDIFF(), CASE WHEN Categorization
-- Analytical Note: Evaluates elapsed calendar days from publication to earliest observed
--                  trending snapshot. Conditioned on trending: applies strictly to videos
--                  in this dataset (16,305 unique titles) and does not represent the probability
--                  of trending among all uploaded videos on YouTube India.
-- ------------------------------------------------------------------------------
WITH video_first_trending AS (
    SELECT
        v.video_id,
        v.publish_date,
        MIN(s.trending_date) AS first_trending_date,
        DATEDIFF(MIN(s.trending_date), v.publish_date) AS days_to_first_trend
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.publish_date
)
SELECT
    CASE
        WHEN days_to_first_trend = 0 THEN 'Day 0 (Same Day)'
        WHEN days_to_first_trend BETWEEN 1 AND 2 THEN 'Day 1 - 2 (Rapid)'
        WHEN days_to_first_trend BETWEEN 3 AND 7 THEN 'Day 3 - 7 (Moderate)'
        ELSE 'Over 7 Days (Late / Sleeper)'
    END AS latency_bracket,
    COUNT(*) AS video_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage_share
FROM video_first_trending
GROUP BY latency_bracket
ORDER BY MIN(days_to_first_trend) ASC;

-- ------------------------------------------------------------------------------
-- Query 07: Trending Persistence Distribution (Longevity in Distinct Dates)
-- Concept: CTE, COUNT(DISTINCT trending_date), CASE WHEN Longevity Buckets
-- Analytical Note: Evaluates distinct calendar dates each video appeared on the trending list.
--                  Measures presence across discrete daily scrapes, not uninterrupted feed residency,
--                  continuous retention, or feed exit velocity.
-- ------------------------------------------------------------------------------
WITH video_longevity AS (
    SELECT
        video_id,
        COUNT(DISTINCT trending_date) AS distinct_trending_days
    FROM trending_snapshots
    GROUP BY video_id
)
SELECT
    CASE
        WHEN distinct_trending_days = 1 THEN '1 Day (Single Appearance)'
        WHEN distinct_trending_days = 2 THEN '2 Days'
        WHEN distinct_trending_days BETWEEN 3 AND 5 THEN '3 - 5 Days'
        ELSE 'Over 5 Days (High Longevity)'
    END AS persistence_bracket,
    COUNT(*) AS unique_videos,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage_share
FROM video_longevity
GROUP BY persistence_bracket
ORDER BY MIN(distinct_trending_days) ASC;

-- ------------------------------------------------------------------------------
-- Query 08: Engagement Performance Segmentation via Empirical Tiers
-- Concept: CTE, NULLIF() Division Protection, Multi-Level CASE WHEN Segmentation
-- Business Purpose: Classifies content into 4 engagement performance tiers (High,
--                   Moderate, Low, Minimal) to analyze audience participation intensity.
-- ------------------------------------------------------------------------------
WITH video_metrics AS (
    SELECT
        video_id,
        MAX(views) AS peak_views,
        MAX(likes) AS peak_likes,
        MAX(comment_count) AS peak_comments,
        ROUND((MAX(likes) + MAX(comment_count)) * 100.0 / NULLIF(MAX(views), 0), 4) AS engagement_rate
    FROM trending_snapshots
    GROUP BY video_id
)
SELECT
    CASE
        WHEN engagement_rate >= 5.0 THEN 'Tier 1: High (>= 5.0%)'
        WHEN engagement_rate >= 2.0 AND engagement_rate < 5.0 THEN 'Tier 2: Moderate (2.0% - 4.99%)'
        WHEN engagement_rate >= 0.5 AND engagement_rate < 2.0 THEN 'Tier 3: Low (0.5% - 1.99%)'
        ELSE 'Tier 4: Minimal (< 0.5%)'
    END AS engagement_tier,
    COUNT(*) AS video_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS video_share_pct,
    SUM(peak_views) AS total_observed_peak_views,
    ROUND(AVG(engagement_rate), 4) AS mean_engagement_rate
FROM video_metrics
GROUP BY engagement_tier
ORDER BY MIN(engagement_rate) DESC;
