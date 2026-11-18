"""MediaPulse Business KPI & Media Metrics Engine.

Provides mathematically verified media metrics, engagement rates, interaction ratios,
and multi-day aggregation functions that prevent double-counting cumulative view counts.
"""

from typing import Optional
import numpy as np
import pandas as pd


def calculate_engagement_rate(
    views: pd.Series,
    likes: pd.Series,
    comments: pd.Series,
) -> pd.Series:
    """Calculate standard social engagement rate as percentage of views.

    Formula:
        Engagement Rate (%) = ((likes + comments) / views) * 100

    Guarantees:
        - Division by zero returns 0.0%.
        - Coerces negative inputs to zero.
        - Returns float Series rounded to 4 decimal places.

    Analytical Note:
        Observed averages in sample datasets reflect cohort distributions
        and should not be treated or described as universal industry benchmarks.

    Args:
        views: Series of view counts.
        likes: Series of like counts.
        comments: Series of comment counts.

    Returns:
        Pandas Series of engagement rates in percentage.
    """
    v = pd.to_numeric(views, errors="coerce").fillna(0).clip(lower=0)
    l = pd.to_numeric(likes, errors="coerce").fillna(0).clip(lower=0)
    c = pd.to_numeric(comments, errors="coerce").fillna(0).clip(lower=0)

    interactions = l + c
    # np.where handles division by zero safely
    er = np.where(v > 0, (interactions / v) * 100.0, 0.0)
    return pd.Series(er, index=views.index, dtype=float).round(4)


def calculate_total_interaction_rate(
    views: pd.Series,
    likes: pd.Series,
    dislikes: pd.Series,
    comments: pd.Series,
) -> pd.Series:
    """Calculate total interaction rate (including dislikes) as percentage of views.

    Formula:
        Total Interaction Rate (%) = ((likes + dislikes + comments) / views) * 100

    Args:
        views: Series of view counts.
        likes: Series of like counts.
        dislikes: Series of dislike counts.
        comments: Series of comment counts.

    Returns:
        Pandas Series of total interaction rates in percentage.
    """
    v = pd.to_numeric(views, errors="coerce").fillna(0).clip(lower=0)
    l = pd.to_numeric(likes, errors="coerce").fillna(0).clip(lower=0)
    d = pd.to_numeric(dislikes, errors="coerce").fillna(0).clip(lower=0)
    c = pd.to_numeric(comments, errors="coerce").fillna(0).clip(lower=0)

    total_interactions = l + d + c
    tir = np.where(v > 0, (total_interactions / v) * 100.0, 0.0)
    return pd.Series(tir, index=views.index, dtype=float).round(4)


def calculate_like_ratio(
    likes: pd.Series,
    dislikes: pd.Series,
) -> pd.Series:
    """Calculate sentiment ratio: likes as percentage of total ratings (likes + dislikes).

    Formula:
        Like Ratio (%) = (likes / (likes + dislikes)) * 100

    Args:
        likes: Series of like counts.
        dislikes: Series of dislike counts.

    Returns:
        Pandas Series of like ratios in percentage. If ratings are disabled or zero, returns 0.0.
    """
    l = pd.to_numeric(likes, errors="coerce").fillna(0).clip(lower=0)
    d = pd.to_numeric(dislikes, errors="coerce").fillna(0).clip(lower=0)

    total_ratings = l + d
    ratio = np.where(total_ratings > 0, (l / total_ratings) * 100.0, 0.0)
    return pd.Series(ratio, index=likes.index, dtype=float).round(4)


def add_engagement_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich DataFrame with calculated engagement and sentiment metrics.

    Args:
        df: Input DataFrame containing views, likes, dislikes, comment_count.

    Returns:
        DataFrame enriched with engagement_rate, total_interaction_rate, like_ratio.
    """
    enriched = df.copy()

    if all(col in enriched.columns for col in ["views", "likes", "comment_count"]):
        enriched["engagement_rate"] = calculate_engagement_rate(
            enriched["views"], enriched["likes"], enriched["comment_count"]
        )

    if all(col in enriched.columns for col in ["views", "likes", "dislikes", "comment_count"]):
        enriched["total_interaction_rate"] = calculate_total_interaction_rate(
            enriched["views"], enriched["likes"], enriched["dislikes"], enriched["comment_count"]
        )

    if all(col in enriched.columns for col in ["likes", "dislikes"]):
        enriched["like_ratio"] = calculate_like_ratio(enriched["likes"], enriched["dislikes"])

    return enriched


def compute_video_summary_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate longitudinal daily observations into one summary record per unique video.

    CRITICAL ANALYTICAL RULE:
        We do NOT sum daily view counts, because daily view counts are cumulative.
        Instead, we take the maximum view count (final observed count) and count
        the distinct trending dates to determine trending persistence.

    Args:
        df: Input DataFrame containing cleaned daily trending observations.

    Returns:
        DataFrame with one row per unique video_id and aggregated KPIs.
    """
    if df.empty or "video_id" not in df.columns:
        return pd.DataFrame()

    agg_dict = {
        "title": "first",
        "channel_title": "first",
        "category_title": "first" if "category_title" in df.columns else "first",
        "publish_date": "first" if "publish_date" in df.columns else "first",
        "trending_date": ["min", "max", "nunique"],
        "views": "max",
        "likes": "max",
        "dislikes": "max",
        "comment_count": "max",
        "days_to_trend": "min" if "days_to_trend" in df.columns else "first",
    }

    # Filter to available columns
    available_agg = {col: agg for col, agg in agg_dict.items() if col in df.columns}

    grouped = df.groupby("video_id").agg(available_agg)
    # Flatten multi-level columns
    flat_cols = []
    for col_tuple in grouped.columns:
        if isinstance(col_tuple, tuple):
            if col_tuple[1] in ["", "first"]:
                flat_cols.append(col_tuple[0])
            else:
                flat_cols.append(f"{col_tuple[0]}_{col_tuple[1]}")
        else:
            flat_cols.append(col_tuple)
    grouped.columns = flat_cols

    # Rename for business clarity
    rename_map = {
        "views_max": "peak_views",
        "views": "peak_views",
        "likes_max": "peak_likes",
        "likes": "peak_likes",
        "dislikes_max": "peak_dislikes",
        "dislikes": "peak_dislikes",
        "comment_count_max": "peak_comments",
        "comment_count": "peak_comments",
        "trending_date_min": "first_trending_date",
        "trending_date_max": "last_trending_date",
        "trending_date_nunique": "days_trended",
        "days_to_trend_min": "initial_days_to_trend",
        "days_to_trend": "initial_days_to_trend",
    }
    grouped = grouped.rename(columns={k: v for k, v in rename_map.items() if k in grouped.columns})

    # Calculate video-level peak engagement rate
    if all(col in grouped.columns for col in ["peak_views", "peak_likes", "peak_comments"]):
        grouped["engagement_rate"] = calculate_engagement_rate(
            grouped["peak_views"], grouped["peak_likes"], grouped["peak_comments"]
        )

    return grouped.reset_index()


def compute_channel_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute channel-level performance summary metrics.

    Args:
        df: Input DataFrame of cleaned observations.

    Returns:
        DataFrame with aggregated channel performance metrics.
    """
    if df.empty or "channel_title" not in df.columns:
        return pd.DataFrame()

    video_level = compute_video_summary_kpis(df)

    channel_summary = (
        video_level.groupby("channel_title")
        .agg(
            unique_trending_videos=("video_id", "nunique"),
            total_channel_views=("peak_views", "sum"),
            avg_video_views=("peak_views", "mean"),
            avg_days_trended=("days_trended", "mean"),
            avg_engagement_rate=("engagement_rate", "mean"),
        )
        .reset_index()
    )

    channel_summary["avg_video_views"] = channel_summary["avg_video_views"].round(2)
    channel_summary["avg_days_trended"] = channel_summary["avg_days_trended"].round(2)
    channel_summary["avg_engagement_rate"] = channel_summary["avg_engagement_rate"].round(4)

    return channel_summary.sort_values(by="unique_trending_videos", ascending=False)


def compute_category_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute category-level media performance summary metrics.

    Args:
        df: Input DataFrame of cleaned observations.

    Returns:
        DataFrame with category performance summary metrics.
    """
    cat_col = "category_title" if "category_title" in df.columns else "category_id"
    if df.empty or cat_col not in df.columns:
        return pd.DataFrame()

    video_level = compute_video_summary_kpis(df)

    category_summary = (
        video_level.groupby(cat_col)
        .agg(
            unique_videos=("video_id", "nunique"),
            total_views=("peak_views", "sum"),
            avg_views_per_video=("peak_views", "mean"),
            avg_engagement_rate=("engagement_rate", "mean"),
            avg_days_trended=("days_trended", "mean"),
        )
        .reset_index()
    )

    category_summary["avg_views_per_video"] = category_summary["avg_views_per_video"].round(2)
    category_summary["avg_engagement_rate"] = category_summary["avg_engagement_rate"].round(4)
    category_summary["avg_days_trended"] = category_summary["avg_days_trended"].round(2)

    return category_summary.sort_values(by="unique_videos", ascending=False)
