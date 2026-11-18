-- ==============================================================================
-- MediaPulse — MySQL 8 Database Validation & Reconciliation Queries
-- Verifies row counts, referential integrity, constraints, and analytical metrics.
-- ==============================================================================

USE mediapulse_db;

-- ------------------------------------------------------------------------------
-- 1. Table Volume Verification
-- Expected:
--   categories:          17
--   channels:         1,423
--   videos:          16,305
--   trending_snapshots: 32,265
-- ------------------------------------------------------------------------------
SELECT 'categories' AS table_name, COUNT(*) AS row_count FROM categories
UNION ALL
SELECT 'channels', COUNT(*) FROM channels
UNION ALL
SELECT 'videos', COUNT(*) FROM videos
UNION ALL
SELECT 'trending_snapshots', COUNT(*) FROM trending_snapshots;

-- ------------------------------------------------------------------------------
-- 2. Referential Integrity & Orphan Record Check
-- All counts must equal 0.
-- ------------------------------------------------------------------------------
-- Orphan videos with missing channel
SELECT COUNT(*) AS orphan_videos_no_channel
FROM videos v
LEFT JOIN channels c ON v.channel_id = c.channel_id
WHERE c.channel_id IS NULL;

-- Orphan videos with missing category
SELECT COUNT(*) AS orphan_videos_no_category
FROM videos v
LEFT JOIN categories cat ON v.category_id = cat.category_id
WHERE cat.category_id IS NULL;

-- Orphan snapshots with missing video
SELECT COUNT(*) AS orphan_snapshots_no_video
FROM trending_snapshots s
LEFT JOIN videos v ON s.video_id = v.video_id
WHERE v.video_id IS NULL;

-- ------------------------------------------------------------------------------
-- 3. Duplicate Prevention Check on (video_id, trending_date)
-- Expected count: 0
-- ------------------------------------------------------------------------------
SELECT video_id, trending_date, COUNT(*) AS duplicate_count
FROM trending_snapshots
GROUP BY video_id, trending_date
HAVING COUNT(*) > 1;

-- ------------------------------------------------------------------------------
-- 4. Category Performance & Cumulative Observed Peak Views Reconciliation
-- Reconciles database aggregation against Phase 4 Pandas calculations.
-- Note: Uses peak_views (MAX per video) summed across unique videos.
-- ------------------------------------------------------------------------------
WITH video_peaks AS (
    SELECT
        v.video_id,
        v.category_id,
        MAX(s.views) AS peak_views,
        MAX(s.likes) AS peak_likes,
        MAX(s.comment_count) AS peak_comments,
        COUNT(DISTINCT s.trending_date) AS days_trended
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.category_id
)
SELECT
    c.category_title,
    COUNT(vp.video_id) AS unique_videos,
    ROUND((COUNT(vp.video_id) * 100.0 / 16305), 2) AS share_of_videos_pct,
    SUM(vp.peak_views) AS cumulative_observed_peak_views,
    ROUND(AVG(vp.days_trended), 2) AS mean_days_trended
FROM video_peaks vp
JOIN categories c ON vp.category_id = c.category_id
GROUP BY c.category_title
ORDER BY unique_videos DESC;

-- ------------------------------------------------------------------------------
-- 5. Top 10 Channels by Unique Trending Videos
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
    MAX(vs.peak_views) AS max_single_video_views,
    ROUND(AVG(vs.days_trended), 2) AS mean_days_trended
FROM channels ch
JOIN video_summary vs ON ch.channel_id = vs.channel_id
GROUP BY ch.channel_id, ch.channel_title
ORDER BY unique_videos DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- 6. Time-to-Observed-Trending at Unique-Video Grain
-- Evaluates earliest observed trending appearance.
-- Expected: Day 0 = 420 videos (2.58%), <= 2 days = 15,720 videos (96.41%)
-- ------------------------------------------------------------------------------
WITH earliest_appearance AS (
    SELECT
        v.video_id,
        DATEDIFF(MIN(s.trending_date), v.publish_date) AS days_to_first_trend
    FROM videos v
    JOIN trending_snapshots s ON v.video_id = s.video_id
    GROUP BY v.video_id, v.publish_date
)
SELECT
    COUNT(*) AS total_videos,
    SUM(CASE WHEN days_to_first_trend = 0 THEN 1 ELSE 0 END) AS day_0_videos,
    ROUND(SUM(CASE WHEN days_to_first_trend = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS day_0_pct,
    SUM(CASE WHEN days_to_first_trend <= 2 THEN 1 ELSE 0 END) AS within_2_days_videos,
    ROUND(SUM(CASE WHEN days_to_first_trend <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS within_2_days_pct,
    SUM(CASE WHEN days_to_first_trend <= 7 THEN 1 ELSE 0 END) AS within_7_days_videos,
    ROUND(SUM(CASE WHEN days_to_first_trend <= 7 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS within_7_days_pct
FROM earliest_appearance;

-- ------------------------------------------------------------------------------
-- 7. Index Performance Analysis (EXPLAIN Statements)
-- ------------------------------------------------------------------------------
EXPLAIN SELECT * FROM trending_snapshots WHERE trending_date = '2018-05-10';
EXPLAIN SELECT * FROM videos WHERE channel_id = 1032;
EXPLAIN SELECT * FROM videos WHERE category_id = 24 AND publish_date >= '2018-01-01';
