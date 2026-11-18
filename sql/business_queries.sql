-- ==============================================================================
-- MediaPulse — Phase 6: Advanced SQL Analytics
-- File: sql/business_queries.sql
-- Description: Strategic media intelligence and executive decision queries
--              analyzing publisher market share, engagement efficiency, viral
--              breakout velocity, channel diversification, and timing ROI.
-- Target Database: MySQL Server 8.0+ (mediapulse_db)
-- Analytical Rules:
--   1. Strict video-level aggregation grain to prevent duplicate view summing.
--   2. Observational framing: distinguishes correlation from causation.
--   3. Null and zero-division protection via NULLIF().
-- ==============================================================================

USE mediapulse_db;

-- ------------------------------------------------------------------------------
-- Query 15: Top 10 Media Publishing Channels Portfolio & Longevity
-- Concept: CTE, Multi-Table JOIN, Aggregate Metrics, Distinct Dates
-- Business Purpose: Identifies the top 10 most prolific content publishers,
--                   evaluating their total output, observed reach, and average shelf life.
-- ------------------------------------------------------------------------------
WITH video_summary AS (
    SELECT
        v.video_id,
        v.channel_id,
        MAX(s.views) AS peak_views,
        COUNT(DISTINCT s.trending_date) AS days_trended
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.channel_id
)
SELECT
    ch.channel_title,
    COUNT(vs.video_id) AS unique_videos,
    SUM(vs.peak_views) AS cumulative_observed_peak_views,
    MAX(vs.peak_views) AS max_single_video_views,
    ROUND(AVG(vs.days_trended), 2) AS mean_days_trended
FROM channels ch
JOIN video_summary vs ON ch.channel_id = vs.channel_id
GROUP BY ch.channel_id, ch.channel_title
ORDER BY unique_videos DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- Query 16: Category Rankings by Median Observed Engagement Rate (True 50th Percentile)
-- Concept: Double CTE, ROW_NUMBER(), COUNT(*) OVER(PARTITION BY), Mathematical Median
-- Business Purpose: Proves the Mass Reach vs. Engagement Inversion by isolating the
--                   true 50th percentile engagement rate per category, resistant to outliers.
-- ------------------------------------------------------------------------------
WITH video_engagement AS (
    SELECT
        v.video_id,
        v.category_id,
        cat.category_title,
        ROUND((MAX(s.likes) + MAX(s.comment_count)) * 100.0 / NULLIF(MAX(s.views), 0), 4) AS engagement_rate
    FROM videos v
    JOIN categories cat ON v.category_id = cat.category_id
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.category_id, cat.category_title
),
ranked_engagement AS (
    SELECT
        category_title,
        engagement_rate,
        ROW_NUMBER() OVER(
            PARTITION BY category_title
            ORDER BY engagement_rate ASC, video_id ASC
        ) AS row_asc,
        COUNT(*) OVER(PARTITION BY category_title) AS total_count
    FROM video_engagement
)
SELECT
    category_title,
    total_count AS unique_videos,
    ROUND(AVG(engagement_rate), 4) AS median_engagement_rate
FROM ranked_engagement
WHERE row_asc IN (FLOOR((total_count + 1) / 2.0), CEIL((total_count + 1) / 2.0))
GROUP BY category_title, total_count
ORDER BY median_engagement_rate DESC;

-- ------------------------------------------------------------------------------
-- Query 17: High-Velocity Breakout Analysis (Same-Day Day-0 Viral Induction)
-- Concept: CTE, MIN(trending_date), DATEDIFF(), Conditional Aggregation
-- Business Purpose: Compares immediate Day-0 viral breakouts against standard videos,
--                   testing whether immediate trending entry yields higher peak views.
-- ------------------------------------------------------------------------------
WITH earliest_trending AS (
    SELECT
        v.video_id,
        v.channel_id,
        v.category_id,
        DATEDIFF(MIN(s.trending_date), v.publish_date) AS days_to_trend,
        MAX(s.views) AS peak_views,
        ROUND((MAX(s.likes) + MAX(s.comment_count)) * 100.0 / NULLIF(MAX(s.views), 0), 4) AS engagement_rate
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.channel_id, v.category_id, v.publish_date
)
SELECT
    CASE
        WHEN days_to_trend = 0 THEN 'Same-Day Breakout (Day 0)'
        ELSE 'Standard Induction (Day 1+)'
    END AS induction_speed,
    COUNT(*) AS video_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS video_share_pct,
    ROUND(AVG(peak_views), 2) AS mean_peak_views,
    ROUND(AVG(engagement_rate), 4) AS mean_engagement_rate
FROM earliest_trending
GROUP BY CASE WHEN days_to_trend = 0 THEN 'Same-Day Breakout (Day 0)' ELSE 'Standard Induction (Day 1+)' END;

-- ------------------------------------------------------------------------------
-- Query 18: Cross-Genre Multi-Category Publishing Channels
-- Concept: CTE, COUNT(DISTINCT category_id), CASE WHEN Diversification Tiers
-- Business Purpose: Evaluates creator strategy: analyzes whether single-genre specialists
--                   or multi-genre networks achieve higher output and view volumes.
-- ------------------------------------------------------------------------------
WITH channel_genre_breadth AS (
    SELECT
        ch.channel_id,
        ch.channel_title,
        COUNT(DISTINCT v.category_id) AS genres_published,
        COUNT(DISTINCT v.video_id) AS total_videos,
        SUM(vp.peak_views) AS total_peak_views
    FROM channels ch
    JOIN videos v ON ch.channel_id = v.channel_id
    JOIN (
        SELECT video_id, MAX(views) AS peak_views
        FROM trending_snapshots
        GROUP BY video_id
    ) vp ON v.video_id = vp.video_id
    GROUP BY ch.channel_id, ch.channel_title
)
SELECT
    CASE
        WHEN genres_published = 1 THEN 'Single Genre Specialist'
        WHEN genres_published = 2 THEN 'Dual Genre Publisher'
        ELSE 'Multi-Genre Network (3+ Genres)'
    END AS diversification_tier,
    COUNT(*) AS channel_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS channel_share_pct,
    SUM(total_videos) AS total_videos_produced,
    ROUND(AVG(total_videos), 2) AS avg_videos_per_channel,
    ROUND(AVG(total_peak_views), 2) AS avg_peak_views_per_channel
FROM channel_genre_breadth
GROUP BY diversification_tier
ORDER BY MIN(genres_published) ASC;

-- ------------------------------------------------------------------------------
-- Query 19: Audience Interaction Policy & Comment Status (Observed Associations)
-- Concept: CTE, Boolean Flags, Aggregate Comparison, Safe NULL Division
-- Analytical Note: Evaluates video-level status (v.comments_disabled at earliest observed snapshot).
--                  Differences reflect observational associations, not algorithmic causation;
--                  confounding factors include genre policies, topic sensitivity, and reverse
--                  causation (creators disabling comments in response to negative reception).
-- ------------------------------------------------------------------------------
WITH video_policy AS (
    SELECT
        v.video_id,
        v.comments_disabled,
        v.ratings_disabled,
        MAX(s.views) AS peak_views,
        MAX(s.likes) AS peak_likes,
        MAX(s.dislikes) AS peak_dislikes,
        MAX(s.comment_count) AS peak_comments
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.comments_disabled, v.ratings_disabled
)
SELECT
    CASE
        WHEN comments_disabled = 1 THEN 'Comments Disabled'
        ELSE 'Comments Enabled'
    END AS comments_status,
    COUNT(*) AS video_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS video_share_pct,
    ROUND(AVG(peak_views), 2) AS mean_peak_views,
    ROUND(AVG(peak_likes), 2) AS mean_peak_likes,
    ROUND(AVG(peak_comments), 2) AS mean_peak_comments,
    ROUND(
        AVG((peak_likes + peak_comments) * 100.0 / NULLIF(peak_views, 0)),
        4
    ) AS mean_engagement_rate
FROM video_policy
GROUP BY comments_status;

-- ------------------------------------------------------------------------------
-- Query 20: Publishing Timing Window Distribution (Historical Associations)
-- Concept: CTE, CASE WHEN Temporal Framing, Mean Latency and Engagement
-- Analytical Note: Compares historical performance across upload windows in UTC/IST.
--                  Differences represent observational associations within the 2017-2018
--                  sample; they do not establish that changing upload timing will causally
--                  alter viewer demand or algorithmic distribution.
-- ------------------------------------------------------------------------------
WITH video_timing AS (
    SELECT
        v.video_id,
        v.publish_hour,
        CASE
            WHEN v.publish_hour BETWEEN 12 AND 16 THEN 'Evening Window (12-16 UTC / 17:30-22:29 IST)'
            WHEN v.publish_hour BETWEEN 4 AND 8 THEN 'Morning Window (04-08 UTC / 09:30-14:29 IST)'
            ELSE 'Off-Peak / Night Window'
        END AS time_window,
        MAX(s.views) AS peak_views,
        DATEDIFF(MIN(s.trending_date), v.publish_date) AS days_to_first_trend,
        ROUND((MAX(s.likes) + MAX(s.comment_count)) * 100.0 / NULLIF(MAX(s.views), 0), 4) AS engagement_rate
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.publish_hour, v.publish_date
)
SELECT
    time_window,
    COUNT(*) AS unique_videos,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS upload_share_pct,
    ROUND(AVG(peak_views), 2) AS mean_peak_views,
    ROUND(AVG(days_to_first_trend), 2) AS mean_days_to_trend,
    ROUND(AVG(engagement_rate), 4) AS mean_engagement_rate
FROM video_timing
GROUP BY time_window
ORDER BY unique_videos DESC;
