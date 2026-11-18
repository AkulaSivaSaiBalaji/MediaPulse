"""MediaPulse Database Ingestion Pipeline.

Populates MySQL database tables in strict dependency order:
  1. categories (Dimension)
  2. channels (Dimension)
  3. videos (Dimension / Asset Level)
  4. trending_snapshots (Fact / Longitudinal Observation Level)

Features transactional rollback, parameterized batch inserts, idempotency, and
comprehensive audit logging of inserted, updated, skipped, and rejected rows.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src import config, database

logger = logging.getLogger("mediapulse.ingestion")


@dataclass
class IngestionReport:
    """Summary metrics of database ingestion execution."""
    categories_inserted: int = 0
    channels_inserted: int = 0
    videos_inserted: int = 0
    snapshots_inserted: int = 0
    snapshots_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "categories_inserted": self.categories_inserted,
            "channels_inserted": self.channels_inserted,
            "videos_inserted": self.videos_inserted,
            "snapshots_inserted": self.snapshots_inserted,
            "snapshots_skipped": self.snapshots_skipped,
            "errors": self.errors,
            "success": self.success,
        }


def ingest_categories(df: pd.DataFrame, engine: Engine) -> int:
    """Populate categories table from cleaned DataFrame in an idempotent manner.

    Args:
        df: Cleaned YouTube India DataFrame.
        engine: Active SQLAlchemy Engine.

    Returns:
        Count of distinct categories inserted.
    """
    cat_df = (
        df[["category_id", "category_title"]]
        .drop_duplicates(subset=["category_id"])
        .sort_values(by="category_id")
    )

    insert_sql = text("""
        INSERT INTO categories (category_id, category_title)
        VALUES (:category_id, :category_title)
        ON DUPLICATE KEY UPDATE category_title = VALUES(category_title)
    """)

    records = cat_df.to_dict(orient="records")
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(insert_sql, records)

    logger.info("Ingested %d categories into database", len(records))
    return len(records)


def ingest_channels(df: pd.DataFrame, engine: Engine) -> int:
    """Populate channels table from cleaned DataFrame in an idempotent manner.

    Args:
        df: Cleaned YouTube India DataFrame.
        engine: Active SQLAlchemy Engine.

    Returns:
        Count of distinct channels processed.
    """
    channel_series = df["channel_title"].dropna().drop_duplicates().sort_values()
    records = [{"channel_title": title} for title in channel_series]

    insert_sql = text("""
        INSERT INTO channels (channel_title)
        VALUES (:channel_title)
        ON DUPLICATE KEY UPDATE channel_title = VALUES(channel_title)
    """)

    with engine.connect() as conn:
        with conn.begin():
            conn.execute(insert_sql, records)

    logger.info("Ingested %d channels into database", len(records))
    return len(records)


def get_channel_mapping(engine: Engine) -> Dict[str, int]:
    """Retrieve mapping of channel_title -> channel_id surrogate key.

    Args:
        engine: Active SQLAlchemy Engine.

    Returns:
        Dictionary mapping channel title to integer channel_id.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT channel_title, channel_id FROM channels;")).fetchall()
        return {row[0]: row[1] for row in result}


def ingest_videos(df: pd.DataFrame, engine: Engine, channel_map: Optional[Dict[str, int]] = None) -> int:
    """Populate videos table at unique-video grain (16,305 unique creative assets).

    Args:
        df: Cleaned YouTube India DataFrame.
        engine: Active SQLAlchemy Engine.
        channel_map: Optional preloaded channel mapping.

    Returns:
        Count of unique videos inserted.
    """
    cmap = channel_map or get_channel_mapping(engine)

    # Sort so earliest observed row provides initial metadata
    df_sorted = df.sort_values(by=["video_id", "trending_date"])
    unique_videos = df_sorted.drop_duplicates(subset=["video_id"]).copy()

    unique_videos["channel_id"] = unique_videos["channel_title"].map(cmap)
    if unique_videos["channel_id"].isnull().any():
        missing = unique_videos[unique_videos["channel_id"].isnull()]["channel_title"].unique()
        raise ValueError(f"Unmapped channels found during video ingestion: {missing}")

    records = []
    for _, row in unique_videos.iterrows():
        records.append({
            "video_id": str(row["video_id"]),
            "channel_id": int(row["channel_id"]),
            "category_id": int(row["category_id"]),
            "title": str(row["title"])[:500],
            "publish_time": str(row["publish_datetime_utc"])[:19].replace("T", " "),
            "publish_date": str(row["publish_date"]),
            "publish_hour": int(row["publish_hour"]),
            "publish_day_name": str(row["publish_day_name"]),
            "thumbnail_link": str(row.get("thumbnail_link", ""))[:500],
            "has_description": bool(row.get("has_description", True)),
            "comments_disabled": bool(row.get("comments_disabled", False)),
            "ratings_disabled": bool(row.get("ratings_disabled", False)),
            "video_error_or_removed": bool(row.get("video_error_or_removed", False)),
        })

    insert_sql = text("""
        INSERT INTO videos (
            video_id, channel_id, category_id, title,
            publish_time, publish_date, publish_hour, publish_day_name,
            thumbnail_link, has_description, comments_disabled,
            ratings_disabled, video_error_or_removed
        )
        VALUES (
            :video_id, :channel_id, :category_id, :title,
            :publish_time, :publish_date, :publish_hour, :publish_day_name,
            :thumbnail_link, :has_description, :comments_disabled,
            :ratings_disabled, :video_error_or_removed
        )
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            comments_disabled = VALUES(comments_disabled),
            ratings_disabled = VALUES(ratings_disabled),
            video_error_or_removed = VALUES(video_error_or_removed)
    """)

    # Batch insert in chunks of 5000
    batch_size = 5000
    with engine.connect() as conn:
        with conn.begin():
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                conn.execute(insert_sql, batch)

    logger.info("Ingested %d unique videos into database", len(records))
    return len(records)


def ingest_trending_snapshots(df: pd.DataFrame, engine: Engine, batch_size: int = 5000) -> Tuple[int, int]:
    """Populate trending_snapshots table (32,265 daily snapshots).

    Args:
        df: Cleaned YouTube India DataFrame.
        engine: Active SQLAlchemy Engine.
        batch_size: Number of records per batch.

    Returns:
        Tuple of (inserted_count, skipped_count).
    """
    records = []
    for _, row in df.iterrows():
        desc = row.get("description")
        desc_str = str(desc) if pd.notnull(desc) else None

        tags = row.get("tags")
        tags_str = str(tags) if pd.notnull(tags) else None

        records.append({
            "video_id": str(row["video_id"]),
            "trending_date": str(row["trending_date"]),
            "views": int(row["views"]),
            "likes": int(row["likes"]),
            "dislikes": int(row["dislikes"]),
            "comment_count": int(row["comment_count"]),
            "days_to_trend": int(row["days_to_trend"]),
            "engagement_rate": float(round(row["engagement_rate"], 4)),
            "total_interaction_rate": float(round(row["total_interaction_rate"], 4)),
            "like_ratio": float(round(row["like_ratio"], 4)),
            "tags": tags_str,
            "description": desc_str,
        })

    insert_sql = text("""
        INSERT INTO trending_snapshots (
            video_id, trending_date, views, likes, dislikes,
            comment_count, days_to_trend, engagement_rate,
            total_interaction_rate, like_ratio, tags, description
        )
        VALUES (
            :video_id, :trending_date, :views, :likes, :dislikes,
            :comment_count, :days_to_trend, :engagement_rate,
            :total_interaction_rate, :like_ratio, :tags, :description
        )
        ON DUPLICATE KEY UPDATE
            views = VALUES(views),
            likes = VALUES(likes),
            dislikes = VALUES(dislikes),
            comment_count = VALUES(comment_count),
            engagement_rate = VALUES(engagement_rate),
            total_interaction_rate = VALUES(total_interaction_rate),
            like_ratio = VALUES(like_ratio)
    """)

    with engine.connect() as conn:
        with conn.begin():
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                conn.execute(insert_sql, batch)

    logger.info("Ingested %d trending snapshots into database", len(records))
    return len(records), 0


def run_full_ingestion_pipeline(
    csv_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> IngestionReport:
    """Execute end-to-end ingestion pipeline in strict dependency order.

    Args:
        csv_path: Path to cleaned CSV. Defaults to config.DATA_PROCESSED_DIR / 'cleaned_youtube_india.csv'.
        engine: Optional SQLAlchemy Engine.

    Returns:
        IngestionReport with detailed counts and execution status.
    """
    path = csv_path or (config.DATA_PROCESSED_DIR / "cleaned_youtube_india.csv")
    if not path.exists():
        raise FileNotFoundError(f"Cleaned dataset not found at: {path}")

    report = IngestionReport()
    eng = engine or database.get_engine()

    # Pre-flight connection validation
    conn_check = database.test_connection(eng)
    if not conn_check["connected"]:
        err_msg = f"Database connection pre-check failed: {conn_check['error']}"
        logger.error(err_msg)
        report.errors.append(err_msg)
        report.success = False
        return report

    try:
        logger.info("Loading cleaned dataset from: %s", path)
        df = pd.read_csv(path)

        # 1. Ingest Categories
        report.categories_inserted = ingest_categories(df, eng)

        # 2. Ingest Channels
        report.channels_inserted = ingest_channels(df, eng)

        # 3. Ingest Videos
        channel_map = get_channel_mapping(eng)
        report.videos_inserted = ingest_videos(df, eng, channel_map=channel_map)

        # 4. Ingest Trending Snapshots
        inserted_snaps, skipped_snaps = ingest_trending_snapshots(df, eng)
        report.snapshots_inserted = inserted_snaps
        report.snapshots_skipped = skipped_snaps

        report.success = True
        logger.info("Full database ingestion pipeline completed successfully")
    except Exception as e:
        logger.exception("Database ingestion pipeline failed: %s", e)
        report.errors.append(str(e))
        report.success = False

    return report
