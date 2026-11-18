-- ==============================================================================
-- File: sql/powerbi_reporting_views.sql
-- Project: MediaPulse — Media Performance & Audience Analytics
-- Target Architecture: MySQL 8.0 -> Power BI Semantic Model (Import Mode)
-- Description: Production SQL reporting views designed for Power BI consumption.
--              Exposes a clean dimensional star schema (4 Dimensions + 1 Fact Table),
--              encapsulates complex joins, resolves grain boundaries, and pre-calculates
--              authoritative video-level lifetime reach metrics.
-- ==============================================================================

USE mediapulse_db;

-- ------------------------------------------------------------------------------
-- 1. DimCategory View: Content Classification Dimension
-- Grain: 1 row per unique YouTube category (17 categories)
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dim_category;

CREATE OR REPLACE VIEW vw_dim_category AS
SELECT 
    category_id,
    category_title,
    created_at AS ingested_at
FROM categories;


-- ------------------------------------------------------------------------------
-- 2. DimChannel View: Publisher / Creator Dimension
-- Grain: 1 row per unique YouTube channel (1,423 channels)
-- Note: Evaluated on binary collation (`utf8mb4_bin`) to preserve publisher casing.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dim_channel;

CREATE OR REPLACE VIEW vw_dim_channel AS
SELECT 
    channel_id,
    channel_title,
    created_at AS ingested_at
FROM channels;


-- ------------------------------------------------------------------------------
-- 3. DimVideo View: Canonical Creative Asset Dimension
-- Grain: 1 row per unique video asset (16,305 videos)
-- Architecture Decision: Encapsulates video-level lifetime aggregates (peak views,
-- peak likes, peak comments, lifetime engagement rate, days to first trend)
-- directly within the dimension to eliminate slow nested DAX iterators in Power BI.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dim_video;

CREATE OR REPLACE VIEW vw_dim_video AS
SELECT 
    v.video_id,
    v.channel_id,
    v.category_id,
    v.title AS video_title,
    v.publish_time,
    v.publish_date,
    v.publish_hour,
    v.publish_day_name,
    v.thumbnail_link,
    v.has_description,
    v.comments_disabled AS comments_disabled_earliest,
    v.ratings_disabled AS ratings_disabled_earliest,
    v.video_error_or_removed AS video_error_or_removed_earliest,
    
    -- Longitudinal Trending Lifecycle Attributes
    MIN(s.trending_date) AS first_trending_date,
    MAX(s.trending_date) AS last_trending_date,
    COUNT(DISTINCT s.trending_date) AS distinct_trending_days,
    DATEDIFF(MIN(s.trending_date), v.publish_date) AS days_to_first_trend,
    
    -- Lifetime Peak Performance Measures
    MAX(s.views) AS peak_views,
    MAX(s.likes) AS peak_likes,
    MAX(s.dislikes) AS peak_dislikes,
    MAX(s.comment_count) AS peak_comments,
    
    -- Lifetime Engagement Intensity KPI: (Likes + Comments) / Views * 100
    ROUND((MAX(s.likes) + MAX(s.comment_count)) * 100.0 / NULLIF(MAX(s.views), 0), 4) AS lifetime_engagement_rate,
    
    -- Categorical Flags for Rapid Slicing
    CASE 
        WHEN DATEDIFF(MIN(s.trending_date), v.publish_date) = 0 THEN 1 
        ELSE 0 
    END AS is_same_day_trending,
    
    CASE 
        WHEN DATEDIFF(MIN(s.trending_date), v.publish_date) <= 2 THEN 1 
        ELSE 0 
    END AS is_trending_within_2days

FROM videos v
JOIN trending_snapshots s ON v.video_id = s.video_id
GROUP BY 
    v.video_id, 
    v.channel_id, 
    v.category_id, 
    v.title, 
    v.publish_time, 
    v.publish_date, 
    v.publish_hour, 
    v.publish_day_name, 
    v.thumbnail_link, 
    v.has_description, 
    v.comments_disabled, 
    v.ratings_disabled, 
    v.video_error_or_removed;


-- ------------------------------------------------------------------------------
-- 4. FactTrendingSnapshots View: Daily Observational Facts
-- Grain: 1 row per daily trending observation (32,265 rows)
-- Note: Views, likes, and comments are cumulative point-in-time metrics.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_fact_trending_snapshots;

CREATE OR REPLACE VIEW vw_fact_trending_snapshots AS
SELECT 
    s.snapshot_id,
    s.video_id,
    s.trending_date,
    s.views,
    s.likes,
    s.dislikes,
    s.comment_count,
    s.comments_disabled,
    s.ratings_disabled,
    s.video_error_or_removed,
    s.days_to_trend AS snapshot_days_to_trend,
    s.engagement_rate AS snapshot_engagement_rate,
    s.total_interaction_rate AS snapshot_total_interaction_rate,
    s.like_ratio AS snapshot_like_ratio,
    s.created_at AS snapshot_ingested_at
FROM trending_snapshots s;


-- ------------------------------------------------------------------------------
-- 5. DimDate View: Unified Calendar Dimension (Recursive CTE)
-- Grain: 1 row per calendar date (2017-05-01 to 2018-06-30 = 426 dates)
-- Role: Active relationship to FactTrendingSnapshot[trending_date];
--       Inactive role-playing relationship to DimVideo[publish_date].
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dim_date;

CREATE OR REPLACE VIEW vw_dim_date AS
WITH RECURSIVE calendar_generator AS (
    SELECT CAST('2017-05-01' AS DATE) AS calendar_date
    UNION ALL
    SELECT DATE_ADD(calendar_date, INTERVAL 1 DAY)
    FROM calendar_generator
    WHERE calendar_date < '2018-06-30'
)
SELECT 
    d.calendar_date AS full_date,
    YEAR(d.calendar_date) AS calendar_year,
    MONTH(d.calendar_date) AS month_number,
    DATE_FORMAT(d.calendar_date, '%M') AS month_name,
    DATE_FORMAT(d.calendar_date, '%b') AS month_short,
    DATE_FORMAT(d.calendar_date, '%Y-%m') AS year_month_label,
    CAST(DATE_FORMAT(d.calendar_date, '%Y%m') AS UNSIGNED) AS year_month_sort,
    CONCAT('Q', QUARTER(d.calendar_date)) AS quarter_name,
    WEEK(d.calendar_date, 3) AS iso_week_number,
    DAYOFWEEK(d.calendar_date) AS day_of_week_num, -- 1 = Sun, 7 = Sat
    WEEKDAY(d.calendar_date) + 1 AS iso_weekday_num, -- 1 = Mon, 7 = Sun
    DATE_FORMAT(d.calendar_date, '%W') AS weekday_name,
    DATE_FORMAT(d.calendar_date, '%a') AS weekday_short,
    
    -- Historical Collection Coverage Flag (distinguishes missing collection dates)
    CASE 
        WHEN ts.trending_date IS NOT NULL THEN 1 
        ELSE 0 
    END AS is_trending_snapshot_date

FROM calendar_generator d
LEFT JOIN (
    SELECT DISTINCT trending_date 
    FROM trending_snapshots
) ts ON d.calendar_date = ts.trending_date;
