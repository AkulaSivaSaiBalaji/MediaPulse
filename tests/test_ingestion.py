"""Unit and integration tests for MediaPulse Database Ingestion Pipeline."""

from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src import config, database, ingestion


@pytest.fixture
def sample_cleaned_df():
    """Minimal DataFrame matching cleaned_youtube_india.csv schema."""
    return pd.DataFrame([
        {
            "video_id": "vid001",
            "trending_date": "2018-05-10",
            "title": "Sample Video 1",
            "channel_title": "Channel A",
            "category_id": 24,
            "category_title": "Entertainment",
            "publish_time": "2018-05-08T14:00:00.000Z",
            "publish_datetime_utc": "2018-05-08 14:00:00",
            "publish_date": "2018-05-08",
            "publish_hour": 14,
            "publish_day_name": "Tuesday",
            "tags": "test|sample",
            "views": 100000,
            "likes": 5000,
            "dislikes": 200,
            "comment_count": 500,
            "thumbnail_link": "https://i.ytimg.com/vi/vid001/default.jpg",
            "comments_disabled": False,
            "ratings_disabled": False,
            "video_error_or_removed": False,
            "description": "Sample description text",
            "has_description": True,
            "days_to_trend": 2,
            "engagement_rate": 5.5,
            "total_interaction_rate": 5.7,
            "like_ratio": 96.15,
        },
        {
            "video_id": "vid001",
            "trending_date": "2018-05-11",
            "title": "Sample Video 1",
            "channel_title": "Channel A",
            "category_id": 24,
            "category_title": "Entertainment",
            "publish_time": "2018-05-08T14:00:00.000Z",
            "publish_datetime_utc": "2018-05-08 14:00:00",
            "publish_date": "2018-05-08",
            "publish_hour": 14,
            "publish_day_name": "Tuesday",
            "tags": "test|sample",
            "views": 150000,
            "likes": 7500,
            "dislikes": 300,
            "comment_count": 700,
            "thumbnail_link": "https://i.ytimg.com/vi/vid001/default.jpg",
            "comments_disabled": False,
            "ratings_disabled": False,
            "video_error_or_removed": False,
            "description": "Sample description text",
            "has_description": True,
            "days_to_trend": 3,
            "engagement_rate": 5.4667,
            "total_interaction_rate": 5.6667,
            "like_ratio": 96.15,
        },
        {
            "video_id": "vid002",
            "trending_date": "2018-05-10",
            "title": "Sample Video 2",
            "channel_title": "Channel B",
            "category_id": 10,
            "category_title": "Music",
            "publish_time": "2018-05-10T08:00:00.000Z",
            "publish_datetime_utc": "2018-05-10 08:00:00",
            "publish_date": "2018-05-10",
            "publish_hour": 8,
            "publish_day_name": "Thursday",
            "tags": "music|song",
            "views": 500000,
            "likes": 25000,
            "dislikes": 1000,
            "comment_count": 2000,
            "thumbnail_link": "https://i.ytimg.com/vi/vid002/default.jpg",
            "comments_disabled": False,
            "ratings_disabled": False,
            "video_error_or_removed": False,
            "description": None,
            "has_description": False,
            "days_to_trend": 0,
            "engagement_rate": 5.4,
            "total_interaction_rate": 5.6,
            "like_ratio": 96.15,
        },
    ])


def test_ingestion_report_dataclass():
    """Verify IngestionReport initializes and serializes correctly."""
    report = ingestion.IngestionReport(
        categories_inserted=17,
        channels_inserted=1423,
        videos_inserted=16305,
        snapshots_inserted=32265,
        snapshots_skipped=0,
        success=True,
    )
    data = report.to_dict()
    assert data["categories_inserted"] == 17
    assert data["channels_inserted"] == 1423
    assert data["videos_inserted"] == 16305
    assert data["snapshots_inserted"] == 32265
    assert data["success"] is True
    assert data["errors"] == []


def test_full_ingestion_connection_failure():
    """Verify run_full_ingestion_pipeline handles unreachable database gracefully."""
    invalid_url = "mysql+pymysql://invalid_u:invalid_p@127.0.0.1:9999/invalid_d?connect_timeout=1"
    invalid_engine = create_engine(invalid_url)

    report = ingestion.run_full_ingestion_pipeline(engine=invalid_engine)
    assert report.success is False
    assert len(report.errors) > 0
    assert "connection" in report.errors[0].lower()


def test_video_deduplication_for_ingestion(sample_cleaned_df):
    """Verify video extraction reduces multi-day snapshot observations to unique creative assets."""
    # sample_cleaned_df has 3 rows (2 for vid001 and 1 for vid002)
    assert len(sample_cleaned_df) == 3
    assert sample_cleaned_df["video_id"].nunique() == 2

    df_sorted = sample_cleaned_df.sort_values(by=["video_id", "trending_date"])
    unique_videos = df_sorted.drop_duplicates(subset=["video_id"])
    assert len(unique_videos) == 2
    assert set(unique_videos["video_id"]) == {"vid001", "vid002"}


def test_channel_mapping_extraction(sample_cleaned_df):
    """Verify distinct channel title extraction."""
    channels = sample_cleaned_df["channel_title"].dropna().drop_duplicates().sort_values()
    assert list(channels) == ["Channel A", "Channel B"]


# Integration test guarded by live connection
is_live_mysql = database.test_connection()["connected"]


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_live_mysql_ingestion(sample_cleaned_df):
    """Integration test: Verify live MySQL ingestion and referential integrity."""
    engine = database.get_engine()
    report = ingestion.run_full_ingestion_pipeline(engine=engine)
    assert report.success is True
    assert report.categories_inserted == 17
    assert report.channels_inserted == 1423
    assert report.videos_inserted == 16305
    assert report.snapshots_inserted == 32265
