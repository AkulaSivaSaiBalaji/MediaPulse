-- ==============================================================================
-- MediaPulse — MySQL 8 Relational Database Schema
-- Normalized relational model for YouTube India media performance analytics.
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS mediapulse_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE mediapulse_db;

-- Drop tables in reverse dependency order if recreating
DROP TABLE IF EXISTS trending_snapshots;
DROP TABLE IF EXISTS videos;
DROP TABLE IF EXISTS channels;
DROP TABLE IF EXISTS categories;

-- ==============================================================================
-- 1. Categories Table (Dimension)
-- Maps official YouTube category IDs to verified human-readable titles.
-- ==============================================================================
CREATE TABLE categories (
    category_id INT NOT NULL,
    category_title VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_category_title (category_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 2. Channels Table (Dimension)
-- Captures publishing media channels.
-- Note: Historical Kaggle YouTube datasets provide channel titles without the
-- 24-character YouTube Channel ID; surrogate auto-increment key is utilized.
-- ==============================================================================
CREATE TABLE channels (
    channel_id INT AUTO_INCREMENT NOT NULL,
    channel_title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (channel_id),
    UNIQUE KEY uq_channel_title (channel_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 3. Videos Table (Dimension / Asset Level)
-- Stores immutable video asset metadata at the unique video grain.
-- Preserves the standard 11-character YouTube video identifier.
-- ==============================================================================
CREATE TABLE videos (
    video_id VARCHAR(20) NOT NULL,
    channel_id INT NOT NULL,
    category_id INT NOT NULL,
    title TEXT NOT NULL,
    publish_time DATETIME NOT NULL,
    publish_date DATE NOT NULL,
    publish_hour TINYINT NOT NULL,
    publish_day_name VARCHAR(15) NOT NULL,
    thumbnail_link VARCHAR(500) NULL,
    has_description BOOLEAN NOT NULL DEFAULT TRUE,
    comments_disabled BOOLEAN NOT NULL DEFAULT FALSE,
    ratings_disabled BOOLEAN NOT NULL DEFAULT FALSE,
    video_error_or_removed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (video_id),
    CONSTRAINT fk_videos_channel FOREIGN KEY (channel_id)
        REFERENCES channels (channel_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_videos_category FOREIGN KEY (category_id)
        REFERENCES categories (category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_videos_channel (channel_id),
    INDEX idx_videos_category (category_id),
    INDEX idx_videos_publish_date (publish_date),
    INDEX idx_videos_publish_hour (publish_hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- 4. Trending Snapshots Table (Fact / Longitudinal Observation Level)
-- Captures daily snapshot metrics for active trending videos.
-- Enforces uniqueness on (video_id, trending_date) to prevent duplicate refreshes.
-- ==============================================================================
CREATE TABLE trending_snapshots (
    snapshot_id INT AUTO_INCREMENT NOT NULL,
    video_id VARCHAR(20) NOT NULL,
    trending_date DATE NOT NULL,
    views BIGINT NOT NULL,
    likes BIGINT NOT NULL,
    dislikes BIGINT NOT NULL,
    comment_count BIGINT NOT NULL,
    days_to_trend INT NOT NULL,
    engagement_rate DECIMAL(8, 4) NOT NULL,
    total_interaction_rate DECIMAL(8, 4) NOT NULL,
    like_ratio DECIMAL(8, 4) NOT NULL,
    tags TEXT NULL,
    description LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_id),
    CONSTRAINT fk_snapshots_video FOREIGN KEY (video_id)
        REFERENCES videos (video_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_video_trending_date UNIQUE KEY (video_id, trending_date),
    INDEX idx_snapshots_trending_date (trending_date),
    INDEX idx_snapshots_views (views DESC),
    INDEX idx_snapshots_engagement (engagement_rate DESC),
    INDEX idx_snapshots_days_to_trend (days_to_trend)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
