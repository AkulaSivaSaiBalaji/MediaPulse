"""Tests for MediaPulse Exploratory Data Analysis (EDA) Module."""

from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from src import eda, config


@pytest.fixture
def cleaned_dataset():
    """Load the cleaned dataset produced in Phase 3."""
    csv_path = config.DATA_PROCESSED_DIR / "cleaned_youtube_india.csv"
    if not csv_path.exists():
        pytest.skip("Cleaned dataset not found; run cleaning pipeline first.")
    return pd.read_csv(csv_path)


def test_daily_trending_activity_grain(cleaned_dataset):
    """Verify daily aggregation produces correct grain and total_observations >= unique_videos."""
    daily = eda.compute_daily_trending_activity(cleaned_dataset)
    assert not daily.empty
    assert len(daily) == cleaned_dataset["trending_date"].nunique()
    assert (daily["total_observations"] >= daily["unique_videos"]).all()
    assert daily["total_observations"].sum() == len(cleaned_dataset)


def test_monthly_trending_activity(cleaned_dataset):
    """Verify monthly aggregation produces valid year-month periods."""
    monthly = eda.compute_monthly_trending_activity(cleaned_dataset)
    assert not monthly.empty
    assert monthly["total_observations"].sum() == len(cleaned_dataset)
    assert "year_month" in monthly.columns


def test_category_performance_no_double_counting(cleaned_dataset):
    """Verify category summary uses video-level grain without double-counting."""
    cat_summary = eda.compute_category_performance_summary(cleaned_dataset)
    assert not cat_summary.empty
    assert cat_summary["unique_videos"].sum() == cleaned_dataset["video_id"].nunique()
    assert (cat_summary["median_views"] > 0).all()
    assert (cat_summary["median_engagement_rate"] >= 0).all()
    assert (cat_summary["mean_days_trended"] >= 1.0).all()


def test_channel_performance_summary(cleaned_dataset):
    """Verify top channel ranking returns exactly top_n channels."""
    top_channels = eda.compute_channel_performance_summary(cleaned_dataset, top_n=10)
    assert len(top_channels) == 10
    assert top_channels["unique_videos"].is_monotonic_decreasing
    assert (top_channels["unique_videos"] > 0).all()


def test_engagement_correlations(cleaned_dataset):
    """Verify Pearson and Spearman rank correlations between engagement metrics."""
    corrs = eda.compute_engagement_correlations(cleaned_dataset)
    assert "pearson_views_likes" in corrs
    assert "spearman_views_likes" in corrs
    assert 0.0 < corrs["spearman_views_likes"] <= 1.0
    assert 0.0 < corrs["spearman_views_comments"] <= 1.0


def test_time_to_trend_summary(cleaned_dataset):
    """Verify time to observed trending summary statistics across categories at unique-video grain."""
    summary = eda.compute_time_to_trend_summary(cleaned_dataset)
    assert not summary.empty
    assert (summary["median_days_to_trend"] >= 0).all()
    assert (summary["min_days"] >= 0).all()


def test_video_time_to_trend_stats(cleaned_dataset):
    """Verify video-level time to observed trending statistics and denominators."""
    stats = eda.compute_video_time_to_trend_stats(cleaned_dataset)
    assert stats["total_unique_videos"] == cleaned_dataset["video_id"].nunique()
    assert stats["median_days"] == 1.0
    assert stats["day_0_count"] == 420
    assert stats["day_0_pct"] == pytest.approx(2.58, abs=0.05)
    assert stats["within_2_days_pct"] == pytest.approx(96.41, abs=0.05)
    assert stats["within_7_days_pct"] == pytest.approx(99.88, abs=0.05)


def test_trending_persistence_summary(cleaned_dataset):
    """Verify trending persistence summary produces valid bracket percentages summing to ~100%."""
    persistence = eda.compute_trending_persistence_summary(cleaned_dataset)
    assert not persistence.empty
    assert len(persistence) == 5
    assert persistence["video_count"].sum() == cleaned_dataset["video_id"].nunique()
    assert pytest.approx(100.0, abs=0.1) == persistence["percentage"].sum()


def test_publication_patterns(cleaned_dataset):
    """Verify publication patterns capture 7 weekdays and 24 UTC hours."""
    weekday_df, hour_df = eda.compute_publication_patterns(cleaned_dataset)
    assert len(weekday_df) == 7
    assert len(hour_df) == 24
    assert (weekday_df["unique_videos"] > 0).all()
    assert (hour_df["unique_videos"] > 0).all()


def test_empty_dataframe_eda():
    """Verify all EDA computation functions handle empty DataFrames gracefully."""
    empty_df = pd.DataFrame()
    assert eda.compute_daily_trending_activity(empty_df).empty
    assert eda.compute_monthly_trending_activity(empty_df).empty
    assert eda.compute_category_performance_summary(empty_df).empty
    assert eda.compute_channel_performance_summary(empty_df).empty
    assert eda.compute_engagement_correlations(empty_df) == {}
    assert eda.compute_time_to_trend_summary(empty_df).empty
    assert eda.compute_video_time_to_trend_stats(empty_df) == {}
    assert eda.compute_trending_persistence_summary(empty_df).empty
    w, h = eda.compute_publication_patterns(empty_df)
    assert w.empty and h.empty


def test_figure_generation(cleaned_dataset, tmp_path):
    """Verify generation of all 8 figures into destination directory."""
    paths = eda.generate_all_eda_figures(cleaned_dataset, figures_dir=tmp_path)
    assert len(paths) == 8
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 1000  # Non-trivial image file
