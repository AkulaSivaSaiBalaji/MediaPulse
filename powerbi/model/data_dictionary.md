# MediaPulse — Semantic Model Data Dictionary

## 1. Overview

This data dictionary documents all tables, columns, data types, nullability, descriptions, and sample values in the production Power BI semantic model.

---

## 2. Table Specifications

### 2.1 Table: `DimCategory`
- **Source:** `vw_dim_category`
- **Grain:** 1 row per unique YouTube content category.
- **Total Rows:** **17**

| Column Name | Data Type | Key Type | Nullable | Description | Sample Value |
|---|---|---|---|---|---|
| `category_id` | Int64 | Primary Key | No | YouTube category numeric identifier | `24` |
| `category_title` | String | Attribute | No | Content classification title | `"Entertainment"` |
| `ingested_at` | DateTime | Audit | No | System timestamp when record was ingested | `2026-11-18 12:40:00` |

---

### 2.2 Table: `DimChannel`
- **Source:** `vw_dim_channel`
- **Grain:** 1 row per unique publishing channel.
- **Total Rows:** **1,423**

| Column Name | Data Type | Key Type | Nullable | Description | Sample Value |
|---|---|---|---|---|---|
| `channel_id` | Int64 | Primary Key | No | Surrogate integer key for YouTube channel | `593` |
| `channel_title` | String | Attribute | No | Display name of publisher (binary collation) | `"Study IQ education"` |
| `ingested_at` | DateTime | Audit | No | System timestamp when record was ingested | `2026-11-18 12:40:00` |

---

### 2.3 Table: `DimVideo`
- **Source:** `vw_dim_video`
- **Grain:** 1 row per unique creative video asset.
- **Total Rows:** **16,305**

| Column Name | Data Type | Key Type | Nullable | Description | Sample Value |
|---|---|---|---|---|---|
| `video_id` | String | Primary Key | No | 11-character YouTube video alphanumeric identifier | `"-0N9r10xb_0"` |
| `channel_id` | Int64 | Foreign Key | No | References `DimChannel[channel_id]` | `593` |
| `category_id` | Int64 | Foreign Key | No | References `DimCategory[category_id]` | `24` |
| `video_title` | String | Attribute | No | Video title at earliest observed snapshot | `"Sanju | Official Teaser"` |
| `publish_time` | DateTime | Attribute | No | Video publication timestamp (UTC) | `2018-04-24 05:00:15` |
| `publish_date` | Date | Attribute | No | Calendar date of publication (UTC) | `2018-04-24` |
| `publish_hour` | Int64 | Attribute | No | Hour of publication in UTC (0 to 23) | `5` |
| `publish_day_name` | String | Attribute | No | Weekday name of publication | `"Tuesday"` |
| `thumbnail_link` | String | Attribute | No | URL link to video default CDN thumbnail | `"https://i.ytimg.com/..."` |
| `has_description` | Boolean | Flag | No | `TRUE` if description text was non-empty | `TRUE` |
| `comments_disabled_earliest` | Boolean | Flag | No | Status at earliest observed trending snapshot | `FALSE` |
| `ratings_disabled_earliest` | Boolean | Flag | No | Status at earliest observed trending snapshot | `FALSE` |
| `video_error_or_removed_earliest`| Boolean | Flag | No | Status at earliest observed trending snapshot | `FALSE` |
| `first_trending_date` | Date | Attribute | No | Earliest observed trending date in catalog | `2018-04-24` |
| `last_trending_date` | Date | Attribute | No | Latest observed trending date in catalog | `2018-05-02` |
| `distinct_trending_days` | Int64 | Metric | No | Count of distinct snapshot dates observed | `9` |
| `days_to_first_trend` | Int64 | Metric | No | `DATEDIFF(first_trending_date, publish_date)` | `0` |
| `peak_views` | Int64 | Metric | No | Maximum view count observed across snapshots | `44,171,797` |
| `peak_likes` | Int64 | Metric | No | Maximum likes count observed across snapshots | `780,895` |
| `peak_dislikes` | Int64 | Metric | No | Maximum dislikes count observed across snapshots | `34,192` |
| `peak_comments` | Int64 | Metric | No | Maximum comments count observed across snapshots | `47,829` |
| `lifetime_engagement_rate` | Decimal | Metric | No | `(peak_likes + peak_comments) * 100 / peak_views` | `1.8761%` |
| `is_same_day_trending` | Int64 | Flag | No | `1` if `days_to_first_trend = 0`, else `0` | `1` |
| `is_trending_within_2days` | Int64 | Flag | No | `1` if `days_to_first_trend <= 2`, else `0` | `1` |

---

### 2.4 Table: `FactTrendingSnapshot`
- **Source:** `vw_fact_trending_snapshots`
- **Grain:** 1 row per daily snapshot observation.
- **Total Rows:** **32,265**

| Column Name | Data Type | Key Type | Nullable | Description | Sample Value |
|---|---|---|---|---|---|
| `snapshot_id` | Int64 | Primary Key | No | Surrogate key for snapshot record | `1042` |
| `video_id` | String | Foreign Key | No | References `DimVideo[video_id]` | `"-0N9r10xb_0"` |
| `trending_date` | Date | Foreign Key | No | References `DimDate[full_date]` | `2017-11-20` |
| `views` | Int64 | Measure | No | Cumulative view count on snapshot date | `133,438` |
| `likes` | Int64 | Measure | No | Cumulative likes count on snapshot date | `1,381` |
| `dislikes` | Int64 | Measure | No | Cumulative dislikes count on snapshot date | `208` |
| `comment_count` | Int64 | Measure | No | Cumulative comments count on snapshot date | `39` |
| `comments_disabled` | Boolean | Flag | No | Point-in-time status on snapshot date | `FALSE` |
| `ratings_disabled` | Boolean | Flag | No | Point-in-time status on snapshot date | `FALSE` |
| `video_error_or_removed`| Boolean | Flag | No | Point-in-time status on snapshot date | `FALSE` |
| `snapshot_days_to_trend`| Int64 | Attribute | No | Elapsed days from upload to snapshot date | `2` |
| `snapshot_engagement_rate`| Decimal | Metric | No | `(likes + comment_count) * 100 / views` | `1.0642%` |
| `snapshot_total_interaction_rate`| Decimal | Metric | No | `(likes + dislikes + comments) * 100 / views` | `1.2200%` |
| `snapshot_like_ratio` | Decimal | Metric | No | `likes * 100 / (likes + dislikes)` | `86.9100%` |
| `snapshot_ingested_at` | DateTime | Audit | No | Timestamp of database ingestion | `2026-11-18 12:40:00` |

---

### 2.5 Table: `DimDate`
- **Source:** `vw_dim_date`
- **Grain:** 1 row per calendar day.
- **Total Rows:** **426** (2017-05-01 to 2018-06-30)

| Column Name | Data Type | Key Type | Sort By Column | Description | Sample Value |
|---|---|---|---|---|---|
| `full_date` | Date | Primary Key | — | Calendar date | `2017-11-14` |
| `calendar_year` | Int64 | Attribute | — | 4-digit calendar year | `2017` |
| `month_number` | Int64 | Attribute | — | Month integer (1 to 12) | `11` |
| `month_name` | String | Attribute | `month_number` | Full month name | `"November"` |
| `month_short` | String | Attribute | `month_number` | 3-letter month abbreviation | `"Nov"` |
| `year_month_label` | String | Attribute | `year_month_sort`| Year-month label (`YYYY-MM`) | `"2017-11"` |
| `year_month_sort` | Int64 | Sort Column| — | Numeric sort key (`YYYYMM`) | `201711` |
| `quarter_name` | String | Attribute | — | Calendar quarter (`Q1` to `Q4`) | `"Q4"` |
| `iso_week_number` | Int64 | Attribute | — | ISO 8601 week number (1 to 53) | `46` |
| `day_of_week_num` | Int64 | Attribute | — | Day of week integer (1=Sun, 7=Sat)| `3` |
| `iso_weekday_num` | Int64 | Attribute | — | ISO weekday integer (1=Mon, 7=Sun)| `2` |
| `weekday_name` | String | Attribute | `iso_weekday_num`| Full weekday name | `"Tuesday"` |
| `weekday_short` | String | Attribute | `iso_weekday_num`| 3-letter weekday abbreviation | `"Tue"` |
| `is_trending_snapshot_date` | Int64 | Flag | — | `1` if date has snapshots, else `0` | `1` |
