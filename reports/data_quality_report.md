# MediaPulse — Data Quality & Dataset Profiling Report

**Project:** MediaPulse — Media Performance & Audience Analytics  
**Phase:** Phase 2 — Dataset Inspection & Profiling  
**Target Role:** Wipro Analyst L1 (Business Analyst / Data Analyst - Media)  
**Date of Audit:** November 17, 2026  
**Auditor:** Akula Siva Sai Balaji  

---

## 1. Executive Summary

This Data Quality Report provides an exhaustive, mathematically verified audit of the raw YouTube India trending video dataset (`INvideos.csv` and `IN_category_id.json`). 

The raw dataset contains **37,352 observations** across **16 columns**, spanning a 7-month observation period from **November 14, 2017 to June 14, 2018**.

### Key Findings at a Glance

| Metric / Dimension | Calculated Value | Data Quality Status |
| :--- | :--- | :--- |
| **Total Rows Analyzed** | `37,352` | Verified |
| **Total Columns** | `16` | Verified |
| **Raw CSV File Size** | `56.84 MB` (`59,600,439` bytes) | Verified |
| **Unique Video IDs** | `16,307` | High content variety |
| **Unique Channels** | `1,426` | Healthy creator distribution |
| **Missing Values** | `561` in `description` only (1.50%) | High completeness (98.5%+) |
| **Exact Duplicate Rows** | `4,263` (11.41%) | Remediation required in Phase 3 |
| **Composite Key Duplicates `(video_id, trending_date)`** | `4,894` (13.10%) | Remediation required in Phase 3 |
| **Malformed `#NAME?` Identifiers** | `511` records (1.37%) | Excel formula corruption detected |
| **Unmapped Category ID** | Category `29` (105 records) | Missing in regional taxonomy |
| **Engagement Metric Anomalies** | `0` negative views/likes/comments | Clean physical boundaries |

---

## 2. Dataset Schema & Structure

### Column Definitions and Native Data Types

| Column Name | Native Type | Target Logical Type | Description | Null Count |
| :--- | :--- | :--- | :--- | :--- |
| `video_id` | `object` (`str`) | `VARCHAR(20)` | Unique 11-character YouTube video identifier | 0 |
| `trending_date` | `object` (`str`) | `DATE` | Date video appeared on trending list (`YY.DD.MM`) | 0 |
| `title` | `object` (`str`) | `VARCHAR(500)` | Video title | 0 |
| `channel_title` | `object` (`str`) | `VARCHAR(255)` | Name of the publishing channel | 0 |
| `category_id` | `int64` | `INT` | YouTube content category numeric identifier | 0 |
| `publish_time` | `object` (`str`) | `DATETIME` / `TIMESTAMP` | Video publish timestamp in ISO 8601 UTC format | 0 |
| `tags` | `object` (`str`) | `TEXT` | Pipe-delimited list of tags | 0 |
| `views` | `int64` | `BIGINT` | Cumulative view count at time of observation | 0 |
| `likes` | `int64` | `INT` | Cumulative like count | 0 |
| `dislikes` | `int64` | `INT` | Cumulative dislike count | 0 |
| `comment_count` | `int64` | `INT` | Total comments posted on the video | 0 |
| `thumbnail_link` | `object` (`str`) | `VARCHAR(255)` | URL to high-resolution video thumbnail | 0 |
| `comments_disabled` | `bool` | `BOOLEAN` | Flag indicating whether creator closed comment section | 0 |
| `ratings_disabled` | `bool` | `BOOLEAN` | Flag indicating whether like/dislike counts are hidden | 0 |
| `video_error_or_removed`| `bool` | `BOOLEAN` | Flag indicating whether video was removed or privatized | 0 |
| `description` | `object` (`str`) | `TEXT` | Full video description text | **561** |

---

## 3. Data Quality Audit Dimensions

### 3.1 Completeness Audit
- 15 out of 16 columns have **100.0% completeness** (0 null values).
- The `description` column has **561 missing values** (1.50%).
- **Business Impact:** Empty descriptions are standard creator behavior (e.g., short teasers, automated uploads). They do not invalidate engagement tracking.
- **Cleaning Strategy:** Impute missing descriptions with an empty string `""` and create a binary feature `has_description = True/False`.

### 3.2 Uniqueness & Duplication Audit
A fundamental concept in media analytics is distinguishing between **technical scraping duplicates** and **legitimate longitudinal observations**:

1. **Exact Duplicate Rows (`4,263` rows, 11.41%):**
   * These occur when an identical daily snapshot was scraped or appended twice.
   * *Remediation:* Must be eliminated using `df.drop_duplicates()` to avoid inflating view counts, likes, or trending frequency.
2. **Composite Key Duplicates `(video_id, trending_date)` (`4,894` rows, 13.10%):**
   * Multiple records exist for the same video on the exact same trending date, but with slight metric differences (e.g., morning scrape vs. evening scrape).
   * *Remediation:* Keep the latest observation per video per day (`keep='last'` ordered by views).
3. **Multi-Day Trending Persistence (Legitimate Business Phenomenon):**
   * Videos remain trending across consecutive calendar days.
   * The average video trends for **2.29 days**.
   * Top non-corrupted trending video: `rRr1qiJRsXk` trended for **16 days**.
   * *Crucial Analytical Rule:* When calculating total platform views, we **must not sum repeated cumulative view counts** across days for the same video; we must take the maximum or final snapshot per video.

### 3.3 Validity & Identifier Integrity (`#NAME?` Issue)
- **Problem Observed:** Exactly **511 rows** contain `video_id == '#NAME?'`.
- **Root Cause Analysis:** When video IDs begin with a hyphen (`-`) or equals sign (`=`), Microsoft Excel automatically interprets the cell as an Excel formula rather than a text string. When the CSV was edited or exported in Excel, Excel replaced the raw string with `#NAME?`.
- **Downstream Consequence:** In MySQL and Power BI, multiple distinct videos sharing the `#NAME?` primary key will cause foreign key violations, artificial fan-outs, and duplicate key errors.
- **Cleaning Strategy:** Generate deterministic surrogate synthetic video IDs based on MD5 hashing of `(channel_title, title, publish_time)` so distinct videos are properly separated.

### 3.4 Temporal Boundaries & Date Format Audit
- **Trending Date:** Stored in two-digit year, day, month format: `%y.%d.%m` (e.g., `'17.14.11'` represents November 14, 2017).
  * Minimum Trending Date: `2017-11-14`
  * Maximum Trending Date: `2018-06-14`
  * Total Observation Period: **212 calendar days** (7.0 months).
- **Publish Time:** Stored in ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SS.000Z`.
  * Minimum Publish Date: `2017-05-27`
  * Maximum Publish Date: `2018-06-13`
  * Time to Trend (Publication to Trending): Spans from under 1 hour to 171 days (older catalog content experiencing viral resurges).

### 3.5 Numerical Sanity & Physical Boundaries

| Metric | Minimum | Maximum | Mean | Median | Negative Counts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Views** | `4,024` | `125,432,237` | `1,060,477.56` | `304,926.0` | `0` |
| **Likes** | `0` | `2,912,710` | `27,082.72` | `3,069.0` | `0` |
| **Dislikes** | `0` | `1,545,017` | `1,665.08` | `326.0` | `0` |
| **Comments** | `0` | `827,755` | `2,676.99` | `329.0` | `0` |

- **Observation:** Zero negative values detected across all metrics.
- Skewness: High positive right-skewness typical of digital media power-law distributions (mean views ~1.06M vs median ~305K).

### 3.6 Taxonomy & Category Mapping Audit
- The raw dataset has **17 unique category IDs**.
- The `IN_category_id.json` file contains **31 category definitions**.
- **The Category 29 Anomaly:**
  * Category ID `29` appears in **105 observations**.
  * It is missing from `IN_category_id.json`.
  * In the global YouTube category taxonomy, ID `29` represents **"Nonprofits & Activism"**.
  * Inspection of titles (e.g., religious broadcasts, social outreach) confirms this mapping.
  * *Remediation:* Explicitly add `{29: 'Nonprofits & Activism'}` to the category mapping dictionary.

#### Category Distribution in Raw Observations

| Category ID | Category Title | Raw Observation Count | Percentage |
| :--- | :--- | :--- | :--- |
| `24` | Entertainment | `16,712` | 44.74% |
| `25` | News & Politics | `5,241` | 14.03% |
| `10` | Music | `3,858` | 10.33% |
| `23` | Comedy | `3,429` | 9.18% |
| `22` | People & Blogs | `2,624` | 7.03% |
| `1` | Film & Animation | `1,658` | 4.44% |
| `17` | Sports | `731` | 1.96% |
| `26` | Howto & Style | `845` | 2.26% |
| `28` | Science & Technology | `552` | 1.48% |
| `27` | Education | `1,223` | 3.27% |
| `29` | Nonprofits & Activism | `105` | 0.28% |
| *Others* | Autos, Gaming, Travel, Shows | `< 374` | < 1.00% |

---

## 4. Remediation Blueprint for Phase 3 (Data Cleaning)

Based on this audit, the Phase 3 cleaning pipeline will execute the following verified rules:

1. **Deduplication:**
   - Execute `drop_duplicates()` to remove exact identical scrapes (`4,263` records).
   - Resolve same-day duplicates on `(video_id, trending_date)` keeping the highest-view record.
2. **Identifier Standardization:**
   - Detect `#NAME?` video IDs and generate deterministic surrogate identifiers (`SURR_{hash}`) to preserve relational integrity.
3. **Date Standardizations:**
   - Convert `trending_date` using format `%y.%d.%m` into standard ISO date `YYYY-MM-DD`.
   - Convert `publish_time` to UTC datetime and extract `publish_date`, `publish_hour`, and `publish_day_of_week`.
   - Compute `days_to_trend = (trending_date - publish_date).days`.
4. **Missing Value Handling:**
   - Fill null descriptions with `""` and create `has_description` boolean.
5. **Taxonomy Enrichment:**
   - Join `category_id` with enriched mapping dictionary including `29: "Nonprofits & Activism"`.
6. **Export:**
   - Save validated, clean dataset to `data/processed/clean_youtube_trending_data.csv`.
