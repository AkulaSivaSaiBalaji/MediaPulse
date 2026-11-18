"""Tests for MediaPulse Data Cleaning Pipeline."""

import pytest
import pandas as pd
import numpy as np
from src import cleaning, config


@pytest.fixture
def sample_raw_data():
    """Create synthetic sample data matching YouTube schema with typical anomalies."""
    return pd.DataFrame({
        "video_id": [
            "vid_0000001",
            "vid_0000001",  # Same-day duplicate snapshot (lower views)
            "vid_0000001",  # Next-day trending snapshot (legitimate multi-day)
            "#NAME?",       # Corrupted Excel formula error
            "vid_0000002",
            "vid_0000002",  # Exact duplicate row
        ],
        "trending_date": [
            "17.14.11",
            "17.14.11",
            "17.15.11",
            "17.14.11",
            "17.14.11",
            "17.14.11",
        ],
        "title": [
            "Video 1 Morning",
            "Video 1 Evening",
            "Video 1 Day 2",
            "Corrupted Video",
            "Video 2",
            "Video 2",
        ],
        "channel_title": [
            "Channel A",
            "Channel A",
            "Channel A",
            "Channel B",
            "Channel C",
            "Channel C",
        ],
        "category_id": [24, 24, 24, 29, 10, 10],
        "publish_time": [
            "2017-11-13T12:00:00.000Z",
            "2017-11-13T12:00:00.000Z",
            "2017-11-13T12:00:00.000Z",
            "2017-11-12T08:00:00.000Z",
            "2017-11-14T05:00:00.000Z",
            "2017-11-14T05:00:00.000Z",
        ],
        "tags": ["tag1", "tag1", "tag1", "tag2", "tag3", "tag3"],
        "views": [1000, 1500, 2000, 500, 3000, 3000],
        "likes": [100, 150, 200, 50, 300, 300],
        "dislikes": [10, 15, 20, 5, 30, 30],
        "comment_count": [20, 30, 40, 10, 50, 50],
        "thumbnail_link": ["http://thumb.jpg"] * 6,
        "comments_disabled": [False] * 6,
        "ratings_disabled": [False] * 6,
        "video_error_or_removed": [False] * 6,
        "description": ["Desc 1", "Desc 1", "Desc 1", None, "Desc 2", "Desc 2"],
    })


def test_schema_validation_success(sample_raw_data):
    """Verify valid schema passes check with no missing columns."""
    is_valid, missing, unexpected = cleaning.validate_schema(sample_raw_data)
    assert is_valid is True
    assert len(missing) == 0


def test_schema_validation_failure():
    """Verify missing required columns are detected and flagged."""
    incomplete_df = pd.DataFrame({"title": ["Test"], "views": [100]})
    is_valid, missing, unexpected = cleaning.validate_schema(incomplete_df)
    assert is_valid is False
    assert "video_id" in missing
    assert "trending_date" in missing


def test_invalid_identifier_detection():
    """Verify detection of Excel artifacts (#NAME?, #VALUE!), empty strings, and malformed IDs."""
    test_df = pd.DataFrame({
        "video_id": ["#NAME?", "#VALUE!", "", "valid_id_01", "short", "vid_1234567"]
    })
    invalid_mask = cleaning.detect_invalid_identifiers(test_df)
    assert invalid_mask.iloc[0] is True or invalid_mask.iloc[0] == 1   # #NAME?
    assert invalid_mask.iloc[1] is True or invalid_mask.iloc[1] == 1   # #VALUE!
    assert invalid_mask.iloc[2] is True or invalid_mask.iloc[2] == 1   # Empty string
    assert invalid_mask.iloc[3] is False or invalid_mask.iloc[3] == 0  # valid 11-char
    assert invalid_mask.iloc[4] is True or invalid_mask.iloc[4] == 1   # short
    assert invalid_mask.iloc[5] is False or invalid_mask.iloc[5] == 0  # valid 11-char


def test_quarantine_invalid_records(sample_raw_data):
    """Verify invalid records are quarantined and excluded from valid records."""
    valid_df, quarantined_df = cleaning.quarantine_invalid_records(sample_raw_data)
    assert len(quarantined_df) == 1
    assert quarantined_df.iloc[0]["video_id"] == "#NAME?"
    assert len(valid_df) == 5
    assert "#NAME?" not in valid_df["video_id"].values


def test_deduplicate_exact_rows(sample_raw_data):
    """Verify exact duplicate rows are removed cleanly."""
    deduped_df, removed_count = cleaning.deduplicate_exact_rows(sample_raw_data)
    assert removed_count == 1
    assert len(deduped_df) == 5


def test_deduplicate_sameday_snapshots(sample_raw_data):
    """Verify same-day snapshot deduplication selects the highest view snapshot."""
    valid_df, _ = cleaning.quarantine_invalid_records(sample_raw_data)
    exact_deduped, _ = cleaning.deduplicate_exact_rows(valid_df)
    clean_df, removed = cleaning.deduplicate_sameday_snapshots(exact_deduped)

    assert removed == 1  # Morning snapshot removed, evening kept
    # Check that the remaining snapshot for vid_0000001 on 17.14.11 has views == 1500 (highest)
    day1_vid1 = clean_df[(clean_df["video_id"] == "vid_0000001") & (clean_df["trending_date"] == "17.14.11")]
    assert len(day1_vid1) == 1
    assert day1_vid1.iloc[0]["views"] == 1500


def test_preserve_multiday_trending(sample_raw_data):
    """Verify observations of the same video on DIFFERENT dates are preserved."""
    valid_df, _ = cleaning.quarantine_invalid_records(sample_raw_data)
    exact_deduped, _ = cleaning.deduplicate_exact_rows(valid_df)
    clean_df, _ = cleaning.deduplicate_sameday_snapshots(exact_deduped)

    # vid_0000001 should have 2 distinct trending dates: 17.14.11 and 17.15.11
    vid1_records = clean_df[clean_df["video_id"] == "vid_0000001"]
    assert len(vid1_records) == 2
    assert set(vid1_records["trending_date"]) == {"17.14.11", "17.15.11"}


def test_missing_description_handling(sample_raw_data):
    """Verify null descriptions are imputed with empty string and flag is generated."""
    processed = cleaning.handle_missing_values(sample_raw_data)
    assert "has_description" in processed.columns
    assert processed["description"].isnull().sum() == 0
    assert not processed.loc[3, "has_description"]
    assert processed.loc[3, "description"] == ""
    assert bool(processed.loc[0, "has_description"]) is True



def test_standardize_dates(sample_raw_data):
    """Verify date parsing to ISO format, publish timestamp parsing, and time to observed trending (days_to_trend)."""
    processed = cleaning.standardize_dates(sample_raw_data)
    assert "publish_date" in processed.columns
    assert "publish_hour" in processed.columns
    assert "days_to_trend" in processed.columns
    assert "is_negative_duration" in processed.columns
    assert processed["days_to_trend"].min() >= 0
    assert (processed["is_negative_duration"] == False).all()


def test_category_enrichment(sample_raw_data):
    """Verify category title mapping and Category 29 fallback mapping."""
    enriched = cleaning.enrich_categories(sample_raw_data)
    assert "category_title" in enriched.columns
    # Category 24 -> Entertainment
    assert enriched.loc[0, "category_title"] == "Entertainment"
    # Category 29 -> Nonprofits & Activism
    assert enriched.loc[3, "category_title"] == "Nonprofits & Activism"


def test_audit_negative_values():
    """Verify explicit pre-clipping audit accurately counts negative values."""
    df_with_negatives = pd.DataFrame({
        "views": [-100, 500, 1000],
        "likes": [10, -5, 20],
        "dislikes": [1, 2, -3],
        "comment_count": [0, 5, 10],
    })
    neg_audit = cleaning.audit_negative_values(df_with_negatives)
    assert neg_audit["views"] == 1
    assert neg_audit["likes"] == 1
    assert neg_audit["dislikes"] == 1
    assert neg_audit["comment_count"] == 0


def test_validate_numerical_columns_with_audit():
    """Verify pre-clipping audit and defensive lower-bounding at 0."""
    df = pd.DataFrame({
        "views": [-50, 100],
        "likes": [-10, 20],
        "dislikes": [5, -2],
        "comment_count": [0, -1],
    })
    cleaned, audit = cleaning.validate_numerical_columns(df, return_audit=True)
    assert audit == {"views": 1, "likes": 1, "dislikes": 1, "comment_count": 1}
    assert (cleaned["views"] >= 0).all()
    assert (cleaned["likes"] >= 0).all()
    assert (cleaned["dislikes"] >= 0).all()
    assert (cleaned["comment_count"] >= 0).all()
    assert cleaned.loc[0, "views"] == 0
    assert cleaned.loc[1, "views"] == 100


def test_empty_dataframe_cleaning():
    """Verify pipeline handles empty DataFrames gracefully without raising errors."""
    empty_df = pd.DataFrame(columns=cleaning.EXPECTED_COLUMNS)
    deduped, removed = cleaning.deduplicate_exact_rows(empty_df)
    assert len(deduped) == 0
    assert removed == 0

    valid, quarantined = cleaning.quarantine_invalid_records(empty_df)
    assert len(valid) == 0
    assert len(quarantined) == 0


def test_cleaning_pipeline_idempotency():
    """Verify running cleaning pipeline on real data produces identical results and 100% reconciliation."""
    results1 = cleaning.run_cleaning_pipeline()
    results2 = cleaning.run_cleaning_pipeline()

    assert results1["reconciliation_passed"] is True
    assert results2["reconciliation_passed"] is True
    assert results1["raw_rows"] == results2["raw_rows"]
    assert results1["cleaned_valid_rows"] == results2["cleaned_valid_rows"]
    assert results1["quarantined_rows"] == results2["quarantined_rows"]
    assert results1["exact_duplicates_removed"] == results2["exact_duplicates_removed"]
    assert results1["sameday_duplicates_removed"] == results2["sameday_duplicates_removed"]
    assert results1["negative_value_audit"] == {"views": 0, "likes": 0, "dislikes": 0, "comment_count": 0}
