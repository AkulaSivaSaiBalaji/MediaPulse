"""Tests for MediaPulse Business Metrics & KPI Calculation Engine."""

import pytest
import pandas as pd
import numpy as np
from src import metrics


def test_engagement_rate_standard():
    """Verify standard engagement rate: ((likes + comments) / views) * 100."""
    views = pd.Series([10000, 50000, 100000])
    likes = pd.Series([200, 1500, 4000])
    comments = pd.Series([50, 500, 1000])

    er = metrics.calculate_engagement_rate(views, likes, comments)
    # 1. (250 / 10000) * 100 = 2.5000%
    # 2. (2000 / 50000) * 100 = 4.0000%
    # 3. (5000 / 100000) * 100 = 5.0000%
    assert er.iloc[0] == pytest.approx(2.5, abs=0.0001)
    assert er.iloc[1] == pytest.approx(4.0, abs=0.0001)
    assert er.iloc[2] == pytest.approx(5.0, abs=0.0001)


def test_engagement_rate_zero_views_protection():
    """Verify that zero views safely returns 0.0% without ZeroDivisionError."""
    views = pd.Series([0, 0, 1000])
    likes = pd.Series([50, 0, 100])
    comments = pd.Series([10, 0, 20])

    er = metrics.calculate_engagement_rate(views, likes, comments)
    assert er.iloc[0] == 0.0
    assert er.iloc[1] == 0.0
    assert er.iloc[2] == pytest.approx(12.0, abs=0.0001)


def test_engagement_rate_negative_values():
    """Verify negative metric inputs are coerced to zero."""
    views = pd.Series([-500, 1000])
    likes = pd.Series([-50, 100])
    comments = pd.Series([-10, 20])

    er = metrics.calculate_engagement_rate(views, likes, comments)
    assert er.iloc[0] == 0.0
    assert er.iloc[1] == pytest.approx(12.0, abs=0.0001)


def test_total_interaction_rate():
    """Verify total interaction rate: ((likes + dislikes + comments) / views) * 100."""
    views = pd.Series([10000])
    likes = pd.Series([300])
    dislikes = pd.Series([50])
    comments = pd.Series([150])

    tir = metrics.calculate_total_interaction_rate(views, likes, dislikes, comments)
    # (300 + 50 + 150) / 10000 * 100 = 5.0000%
    assert tir.iloc[0] == pytest.approx(5.0, abs=0.0001)


def test_like_ratio():
    """Verify like ratio sentiment formula: (likes / (likes + dislikes)) * 100."""
    likes = pd.Series([900, 100, 0])
    dislikes = pd.Series([100, 100, 0])

    ratio = metrics.calculate_like_ratio(likes, dislikes)
    assert ratio.iloc[0] == pytest.approx(90.0, abs=0.0001)
    assert ratio.iloc[1] == pytest.approx(50.0, abs=0.0001)
    assert ratio.iloc[2] == 0.0  # Zero ratings disabled check


def test_video_summary_kpis_no_double_counting():
    """CRITICAL TEST: Verify that multi-day view counts are NOT summed.

    If a video trends across 3 days with cumulative views 1000, 2000, 3000,
    the peak video views MUST be 3000, NOT the sum (6000).
    """
    multi_day_df = pd.DataFrame({
        "video_id": ["vid_A", "vid_A", "vid_A", "vid_B"],
        "title": ["Title A", "Title A", "Title A", "Title B"],
        "channel_title": ["Chan 1", "Chan 1", "Chan 1", "Chan 2"],
        "category_title": ["Entertainment", "Entertainment", "Entertainment", "Music"],
        "trending_date": ["2018-01-01", "2018-01-02", "2018-01-03", "2018-01-01"],
        "views": [1000, 2000, 3000, 5000],
        "likes": [100, 200, 300, 500],
        "dislikes": [10, 20, 30, 50],
        "comment_count": [10, 20, 30, 50],
        "days_to_trend": [1, 2, 3, 0],
    })

    kpis = metrics.compute_video_summary_kpis(multi_day_df)
    assert len(kpis) == 2

    vid_a = kpis[kpis["video_id"] == "vid_A"].iloc[0]
    assert vid_a["peak_views"] == 3000  # NOT 6000!
    assert vid_a["peak_likes"] == 300
    assert vid_a["days_trended"] == 3
    assert vid_a["first_trending_date"] == "2018-01-01"
    assert vid_a["last_trending_date"] == "2018-01-03"


def test_channel_kpis():
    """Verify channel aggregation correctly rolls up video KPIs."""
    df = pd.DataFrame({
        "video_id": ["v1", "v2"],
        "title": ["T1", "T2"],
        "channel_title": ["MegaChannel", "MegaChannel"],
        "category_title": ["Entertainment", "Entertainment"],
        "trending_date": ["2018-01-01", "2018-01-01"],
        "views": [10000, 20000],
        "likes": [1000, 2000],
        "dislikes": [50, 100],
        "comment_count": [100, 200],
        "days_to_trend": [1, 2],
    })
    ch_kpis = metrics.compute_channel_kpis(df)
    assert len(ch_kpis) == 1
    assert ch_kpis.iloc[0]["unique_trending_videos"] == 2
    assert ch_kpis.iloc[0]["total_channel_views"] == 30000


def test_category_kpis():
    """Verify category benchmarks correctly roll up video KPIs."""
    df = pd.DataFrame({
        "video_id": ["v1", "v2"],
        "title": ["T1", "T2"],
        "channel_title": ["Ch1", "Ch2"],
        "category_title": ["Comedy", "Music"],
        "trending_date": ["2018-01-01", "2018-01-01"],
        "views": [10000, 20000],
        "likes": [1000, 2000],
        "dislikes": [50, 100],
        "comment_count": [100, 200],
        "days_to_trend": [1, 2],
    })
    cat_kpis = metrics.compute_category_kpis(df)
    assert len(cat_kpis) == 2
    assert set(cat_kpis["category_title"]) == {"Comedy", "Music"}


def test_empty_dataframe_metrics():
    """Verify metrics functions handle empty DataFrames safely."""
    empty_df = pd.DataFrame()
    assert metrics.compute_video_summary_kpis(empty_df).empty
    assert metrics.compute_channel_kpis(empty_df).empty
    assert metrics.compute_category_kpis(empty_df).empty
