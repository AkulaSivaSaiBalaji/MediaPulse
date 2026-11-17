"""Tests for the MediaPulse Dataset Profiling & Inspection Module."""

import pytest
import pandas as pd
from src import profiling, config


def test_category_mapping_loading():
    """Verify category mapping loads cleanly and includes category 29 fallback."""
    cat_map = profiling.load_category_mapping()
    assert isinstance(cat_map, dict)
    assert len(cat_map) >= 30
    assert 1 in cat_map  # Film & Animation
    assert 24 in cat_map  # Entertainment
    assert 29 in cat_map  # Nonprofits & Activism
    assert cat_map[24] == "Entertainment"
    assert cat_map[29] == "Nonprofits & Activism"


def test_raw_dataset_loading():
    """Verify loading raw dataset returns DataFrame with expected columns."""
    df, cat_map = profiling.load_raw_dataset()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = [
        "video_id",
        "trending_date",
        "title",
        "channel_title",
        "category_id",
        "publish_time",
        "views",
        "likes",
        "dislikes",
        "comment_count",
    ]
    for col in expected_cols:
        assert col in df.columns


def test_schema_inspection():
    """Verify schema profiling captures dimensions and column types accurately."""
    df, _ = profiling.load_raw_dataset()
    schema = profiling.inspect_schema(df)
    assert schema["total_rows"] == len(df)
    assert schema["total_columns"] == len(df.columns)
    assert "video_id" in schema["columns"]
    assert "views" in schema["dtypes"]


def test_missing_values_audit():
    """Verify null audit correctly identifies missing values in description."""
    df, _ = profiling.load_raw_dataset()
    missing = profiling.audit_missing_values(df)
    assert "description" in missing
    assert missing["description"]["null_count"] > 0
    assert missing["views"]["null_count"] == 0
    assert missing["video_id"]["null_count"] == 0


def test_duplicates_audit():
    """Verify detection of exact row duplicates and composite key duplicates."""
    df, _ = profiling.load_raw_dataset()
    dup_stats = profiling.audit_duplicates(df)
    assert dup_stats["exact_duplicate_rows"] > 0
    assert dup_stats["composite_key_duplicates"] >= dup_stats["exact_duplicate_rows"]


def test_identifiers_audit():
    """Verify detection of Excel formula corruption (#NAME?) in video_id."""
    df, _ = profiling.load_raw_dataset()
    id_stats = profiling.audit_identifiers(df)
    assert "unique_video_ids" in id_stats
    assert id_stats["unique_video_ids"] > 0
    assert id_stats["malformed_excel_name_errors"] > 0
    assert id_stats["unique_channels"] > 0


def test_date_ranges_audit():
    """Verify parsing and calculation of trending and publish date spans."""
    df, _ = profiling.load_raw_dataset()
    date_stats = profiling.audit_date_ranges(df)
    assert date_stats["trending_date_min"] is not None
    assert date_stats["trending_date_max"] is not None
    assert date_stats["trending_days_span"] > 0
    assert date_stats["publish_time_min"] is not None


def test_numeric_metrics_audit():
    """Verify engagement metrics have zero negative values."""
    df, _ = profiling.load_raw_dataset()
    metrics = profiling.audit_numeric_metrics(df)
    for col in ["views", "likes", "dislikes", "comment_count"]:
        assert col in metrics
        assert metrics[col]["negative_count"] == 0
        assert metrics[col]["min"] >= 0
        assert metrics[col]["max"] > 0


def test_category_coverage_audit():
    """Verify category mapping coverage and handling of unmapped IDs."""
    df, cat_map = profiling.load_raw_dataset()
    coverage = profiling.audit_category_coverage(df, cat_map)
    assert coverage["distinct_csv_categories"] > 0
    assert coverage["total_taxonomy_categories"] >= coverage["distinct_csv_categories"]
    assert len(coverage["unmapped_category_ids"]) == 0  # Fallback resolved ID 29


def test_full_data_profile_generation():
    """Verify full end-to-end data profile contains all required sections."""
    profile = profiling.generate_data_profile()
    required_keys = ["schema", "missing_values", "duplicates", "identifiers", "dates", "metrics", "categories"]
    for key in required_keys:
        assert key in profile
