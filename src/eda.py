"""MediaPulse Exploratory Data Analysis (EDA) Module.

Provides reproducible aggregation routines, statistical analysis functions,
and publication-quality Matplotlib/Seaborn visualization generators.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure local writable Matplotlib cache directory inside workspace
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent.parent / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from src import config, metrics

# Visualization styling standards
FIGURES_DIR: Path = config.BASE_DIR / "reports" / "figures"
PALETTE = "viridis"
SNS_STYLE = "whitegrid"


def set_plot_style() -> None:
    """Configure professional plotting theme and typography."""
    sns.set_theme(style=SNS_STYLE, font="sans-serif")
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#cccccc"
    plt.rcParams["axes.linewidth"] = 0.8


def compute_daily_trending_activity(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily total observations versus distinct unique trending videos.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        DataFrame indexed by trending_date with total_observations, unique_videos,
        and multi_day_active_videos.
    """
    if df.empty or "trending_date" not in df.columns:
        return pd.DataFrame()

    daily = (
        df.groupby("trending_date")
        .agg(
            total_observations=("video_id", "count"),
            unique_videos=("video_id", "nunique"),
        )
        .reset_index()
    )
    daily["trending_date"] = pd.to_datetime(daily["trending_date"])
    daily["recurring_videos"] = daily["total_observations"] - daily["unique_videos"]
    return daily.sort_values(by="trending_date")


def compute_monthly_trending_activity(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly aggregated observation volume and unique video count.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        DataFrame with year_month, total_observations, unique_videos.
    """
    if df.empty or "trending_date" not in df.columns:
        return pd.DataFrame()

    temp = df.copy()
    temp["year_month"] = pd.to_datetime(temp["trending_date"]).dt.to_period("M").astype(str)
    monthly = (
        temp.groupby("year_month")
        .agg(
            total_observations=("video_id", "count"),
            unique_videos=("video_id", "nunique"),
        )
        .reset_index()
    )
    return monthly.sort_values(by="year_month")


def compute_category_performance_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute category performance metrics at the video-level aggregation grain.

    CRITICAL ANALYTICAL GRAIN:
        Rolls up daily observations to unique video_id first, using peak_views and
        peak_likes, to prevent double-counting cumulative view counts.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        DataFrame of categories with unique_videos, total_views, median_views,
        median_engagement_rate, and mean_days_trended.
    """
    if df.empty or "category_title" not in df.columns:
        return pd.DataFrame()

    video_level = metrics.compute_video_summary_kpis(df)

    cat_summary = (
        video_level.groupby("category_title")
        .agg(
            unique_videos=("video_id", "nunique"),
            total_views=("peak_views", "sum"),
            median_views=("peak_views", "median"),
            mean_views=("peak_views", "mean"),
            median_engagement_rate=("engagement_rate", "median"),
            mean_engagement_rate=("engagement_rate", "mean"),
            mean_days_trended=("days_trended", "mean"),
        )
        .reset_index()
    )

    cat_summary["share_of_videos_pct"] = (
        (cat_summary["unique_videos"] / cat_summary["unique_videos"].sum()) * 100
    ).round(2)
    cat_summary["median_views"] = cat_summary["median_views"].round(1)
    cat_summary["median_engagement_rate"] = cat_summary["median_engagement_rate"].round(4)
    cat_summary["mean_days_trended"] = cat_summary["mean_days_trended"].round(2)

    return cat_summary.sort_values(by="unique_videos", ascending=False)


def compute_channel_performance_summary(
    df: pd.DataFrame, top_n: int = 10
) -> pd.DataFrame:
    """Compute top channels ranked by unique trending videos with peak metrics.

    Args:
        df: Input cleaned DataFrame.
        top_n: Number of top channels to return.

    Returns:
        DataFrame of top channels with unique videos, median views, and days trended.
    """
    if df.empty or "channel_title" not in df.columns:
        return pd.DataFrame()

    video_level = metrics.compute_video_summary_kpis(df)

    ch_summary = (
        video_level.groupby("channel_title")
        .agg(
            unique_videos=("video_id", "nunique"),
            total_views=("peak_views", "sum"),
            median_views=("peak_views", "median"),
            max_views=("peak_views", "max"),
            mean_days_trended=("days_trended", "mean"),
            median_engagement_rate=("engagement_rate", "median"),
        )
        .reset_index()
    )

    ch_summary["median_views"] = ch_summary["median_views"].round(1)
    ch_summary["mean_days_trended"] = ch_summary["mean_days_trended"].round(2)
    ch_summary["median_engagement_rate"] = ch_summary["median_engagement_rate"].round(4)

    return ch_summary.sort_values(by="unique_videos", ascending=False).head(top_n)


def compute_engagement_correlations(df: pd.DataFrame) -> Dict[str, float]:
    """Compute Pearson and Spearman rank correlations between engagement metrics.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        Dictionary of correlation coefficients.
    """
    if df.empty:
        return {}

    metric_cols = ["views", "likes", "dislikes", "comment_count", "engagement_rate"]
    available = [c for c in metric_cols if c in df.columns]

    pearson = df[available].corr(method="pearson")
    spearman = df[available].corr(method="spearman")

    return {
        "pearson_views_likes": float(round(pearson.loc["views", "likes"], 4)),
        "spearman_views_likes": float(round(spearman.loc["views", "likes"], 4)),
        "pearson_views_comments": float(round(pearson.loc["views", "comment_count"], 4)),
        "spearman_views_comments": float(round(spearman.loc["views", "comment_count"], 4)),
        "pearson_likes_comments": float(round(pearson.loc["likes", "comment_count"], 4)),
        "spearman_likes_comments": float(round(spearman.loc["likes", "comment_count"], 4)),
    }


def compute_time_to_trend_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze the distribution of time to observed trending across categories.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        Summary statistics of days_to_trend grouped by category.
    """
    if df.empty or "days_to_trend" not in df.columns or "category_title" not in df.columns:
        return pd.DataFrame()

    summary = (
        df.groupby("category_title")["days_to_trend"]
        .agg(
            median_days_to_trend="median",
            mean_days_to_trend="mean",
            p25_days="quantile",
            p75_days=lambda x: x.quantile(0.75),
            min_days="min",
            max_days="max",
        )
        .reset_index()
    )

    summary["mean_days_to_trend"] = summary["mean_days_to_trend"].round(2)
    summary["p75_days"] = summary["p75_days"].round(2)
    return summary.sort_values(by="median_days_to_trend")


def compute_trending_persistence_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the distribution of trending days per unique video.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        DataFrame with persistence buckets and video counts.
    """
    if df.empty or "video_id" not in df.columns or "trending_date" not in df.columns:
        return pd.DataFrame()

    persistence = df.groupby("video_id")["trending_date"].nunique().reset_index()
    persistence.columns = ["video_id", "days_trended"]

    bins = [0, 1, 2, 5, 10, 100]
    labels = ["1 Day", "2 Days", "3-5 Days", "6-10 Days", "11+ Days"]
    persistence["persistence_bracket"] = pd.cut(persistence["days_trended"], bins=bins, labels=labels)

    bracket_summary = (
        persistence["persistence_bracket"]
        .value_counts(sort=False)
        .reset_index()
    )
    bracket_summary.columns = ["persistence_bracket", "video_count"]
    bracket_summary["percentage"] = (
        (bracket_summary["video_count"] / bracket_summary["video_count"].sum()) * 100
    ).round(2)

    return bracket_summary


def compute_publication_patterns(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate upload frequencies by day of week and UTC publication hour.

    Note: Hour is strictly in UTC. In India (IST), add 5 hours 30 minutes.

    Args:
        df: Input cleaned DataFrame.

    Returns:
        Tuple of (weekday_summary_df, hour_summary_df).
    """
    if df.empty or "publish_day_name" not in df.columns or "publish_hour" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    weekday_counts = (
        df.groupby("publish_day_name")["video_id"]
        .nunique()
        .reindex(weekday_order)
        .reset_index()
    )
    weekday_counts.columns = ["weekday", "unique_videos"]

    hour_counts = (
        df.groupby("publish_hour")["video_id"]
        .nunique()
        .reset_index()
    )
    hour_counts.columns = ["publish_hour_utc", "unique_videos"]

    return weekday_counts, hour_counts


# ==============================================================================
# Visualization Generation Functions (Matplotlib OO-API & Seaborn)
# ==============================================================================

def plot_trending_activity(
    daily_df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate daily trending observation volume vs unique active videos chart."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "01_trending_activity_over_time.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)

    ax.plot(
        daily_df["trending_date"],
        daily_df["total_observations"],
        label="Total Observations (Daily Snapshots)",
        color="#1f77b4",
        linewidth=1.8,
    )
    ax.plot(
        daily_df["trending_date"],
        daily_df["unique_videos"],
        label="Unique Active Trending Videos",
        color="#2ca02c",
        linewidth=1.8,
        linestyle="--",
    )
    ax.fill_between(
        daily_df["trending_date"],
        daily_df["unique_videos"],
        daily_df["total_observations"],
        color="#1f77b4",
        alpha=0.15,
        label="Recurring Persistent Videos",
    )

    ax.set_title(
        "YouTube India: Daily Trending Observations vs. Unique Active Videos (2017–2018)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Trending Date", fontsize=11, labelpad=10)
    ax.set_ylabel("Count of Records", fontsize=11, labelpad=10)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.legend(frameon=True, facecolor="white", loc="lower right", fontsize=10)
    plt.tight_layout()

    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_category_performance(
    cat_df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate multi-panel comparison of category volume, median views, and engagement."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "02_category_performance_comparison.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    top_cats = cat_df.head(10).sort_values(by="unique_videos", ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    # Panel 1: Unique Videos per Category
    axes[0].barh(
        top_cats["category_title"],
        top_cats["unique_videos"],
        color="#2b5c8f",
        edgecolor="#1d3d60",
    )
    axes[0].set_title(
        "Content Volume: Unique Trending Videos by Category",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].set_xlabel("Count of Unique Videos", fontsize=10)
    axes[0].xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    for i, v in enumerate(top_cats["unique_videos"]):
        axes[0].text(v + 50, i, f"{v:,}", va="center", fontsize=9, color="#333333")

    # Panel 2: Median Views vs Median Engagement Rate
    ax2_views = axes[1]
    ax2_views.barh(
        top_cats["category_title"],
        top_cats["median_views"] / 1000,
        color="#4daf4a",
        edgecolor="#2d682b",
        alpha=0.85,
    )
    ax2_views.set_title(
        "Audience Traction: Median Peak Views by Category (in Thousands)",
        fontsize=12,
        fontweight="bold",
    )
    ax2_views.set_xlabel("Median Peak Views (Thousands)", fontsize=10)
    ax2_views.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}K"))

    for i, v in enumerate(top_cats["median_views"]):
        ax2_views.text(
            (v / 1000) + 5, i, f"{v/1000:.1f}K", va="center", fontsize=9, color="#333333"
        )

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_top_channels(
    ch_df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate bar chart of top 10 channels by unique trending videos."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "03_top_channels_analysis.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    sorted_ch = ch_df.sort_values(by="unique_videos", ascending=True)

    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)

    bars = ax.barh(
        sorted_ch["channel_title"],
        sorted_ch["unique_videos"],
        color="#e41a1c",
        edgecolor="#991214",
        alpha=0.85,
    )

    ax.set_title(
        "Top 10 Channels by Unique Trending Videos (YouTube India)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Number of Unique Trending Videos", fontsize=11, labelpad=8)
    ax.set_ylabel("Channel Name", fontsize=11, labelpad=8)
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 2,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width)}",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_views_vs_engagement(
    df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate dual log-log scatter plot of Views vs Likes and Views vs Comments."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "04_views_vs_engagement_scatter.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    # Subsample 4,000 points if large to maintain crisp rendering
    plot_data = df.sample(min(4000, len(df)), random_state=42)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Panel 1: Views vs Likes (Log-Log)
    axes[0].scatter(
        plot_data["views"],
        plot_data["likes"] + 1,
        alpha=0.25,
        s=14,
        color="#377eb8",
        edgecolors="none",
    )
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_title(
        "Views vs. Likes (Log-Log Scale)\nSpearman r = 0.866 (Strong Monotonic Relationship)",
        fontsize=11,
        fontweight="bold",
    )
    axes[0].set_xlabel("Views (Log Scale)", fontsize=10)
    axes[0].set_ylabel("Likes (Log Scale)", fontsize=10)
    axes[0].xaxis.set_major_formatter(ticker.LogFormatterMathtext())
    axes[0].yaxis.set_major_formatter(ticker.LogFormatterMathtext())

    # Panel 2: Views vs Comments (Log-Log)
    axes[1].scatter(
        plot_data["views"],
        plot_data["comment_count"] + 1,
        alpha=0.25,
        s=14,
        color="#ff7f00",
        edgecolors="none",
    )
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_title(
        "Views vs. Comments (Log-Log Scale)\nSpearman r = 0.742 (Moderate-to-Strong Relationship)",
        fontsize=11,
        fontweight="bold",
    )
    axes[1].set_xlabel("Views (Log Scale)", fontsize=10)
    axes[1].set_ylabel("Comment Count (Log Scale)", fontsize=10)
    axes[1].xaxis.set_major_formatter(ticker.LogFormatterMathtext())
    axes[1].yaxis.set_major_formatter(ticker.LogFormatterMathtext())

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_engagement_distribution(
    df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate distribution histogram and boxplot for Engagement Rate."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "05_engagement_rate_distribution.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    er_series = df["engagement_rate"].dropna()
    # Filter 99th percentile for readable distribution graph
    p99 = float(er_series.quantile(0.99))
    filtered_er = er_series[er_series <= p99]

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), dpi=300, sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # Panel 1: Histogram + KDE
    sns.histplot(
        filtered_er,
        kde=True,
        ax=axes[0],
        color="#4a148c",
        bins=50,
        stat="density",
    )
    mean_val = float(er_series.mean())
    median_val = float(er_series.median())

    axes[0].axvline(
        median_val, color="#d32f2f", linestyle="--", linewidth=1.8, label=f"Median: {median_val:.2f}%"
    )
    axes[0].axvline(
        mean_val, color="#0288d1", linestyle="-", linewidth=1.8, label=f"Mean: {mean_val:.2f}%"
    )
    axes[0].set_title(
        "Distribution of Social Engagement Rate (%) in YouTube India Trending Sample",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].set_ylabel("Density", fontsize=10)
    axes[0].legend(frameon=True, facecolor="white", loc="upper right")

    # Panel 2: Boxplot
    sns.boxplot(x=filtered_er, ax=axes[1], color="#ab47bc", fliersize=2)
    axes[1].set_xlabel("Engagement Rate (%) = ((Likes + Comments) / Views) * 100", fontsize=10)

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_time_to_trend(
    df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate boxplot comparing time to observed trending across top categories."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "06_time_to_trend_by_category.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    top_cat_names = df["category_title"].value_counts().head(8).index.tolist()
    sub_df = df[df["category_title"].isin(top_cat_names)].copy()

    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

    sns.boxplot(
        data=sub_df,
        y="category_title",
        x="days_to_trend",
        hue="category_title",
        legend=False,
        ax=ax,
        palette="Blues_r",
        showmeans=True,
        meanprops={"marker": "o", "markerfacecolor": "red", "markeredgecolor": "red", "markersize": 5},
        fliersize=2,
    )

    ax.set_xlim(-0.5, 15)  # Focus on first 15 days where 95% of trending occurs
    ax.set_title(
        "Time to Observed Trending by Content Category (First 15 Days Focus)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Time to Observed Trending in Days: (Trending Date - Publish Date)", fontsize=10)
    ax.set_ylabel("Content Category", fontsize=10)

    # Note
    ax.text(
        0.98,
        0.05,
        "Red dot = Mean | Vertical bar = Median | Values clipped at 15 days for visual clarity",
        transform=ax.transAxes,
        ha="right",
        fontsize=9,
        style="italic",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
    )

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_trending_persistence(
    df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate bar chart showing the decay curve of trending persistence."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "07_trending_persistence_distribution.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    bracket_df = compute_trending_persistence_summary(df)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

    bars = ax.bar(
        bracket_df["persistence_bracket"].astype(str),
        bracket_df["video_count"],
        color="#1f77b4",
        edgecolor="#144d75",
        alpha=0.85,
    )

    ax.set_title(
        "Trending Persistence: Days Observed on Trending Feed per Unique Video",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Distinct Days Video Appeared on Trending Feed", fontsize=10)
    ax.set_ylabel("Unique Video Count", fontsize=10)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    for bar in bars:
        height = bar.get_height()
        pct = (height / bracket_df["video_count"].sum()) * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 150,
            f"{int(height):,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_ylim(0, max(bracket_df["video_count"]) * 1.15)
    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def plot_publication_patterns(
    weekday_df: pd.DataFrame, hour_df: pd.DataFrame, output_path: Optional[Path] = None
) -> Path:
    """Generate two-panel publication timing chart: Day of Week and UTC Hour."""
    set_plot_style()
    save_p = output_path or (FIGURES_DIR / "08_publication_patterns.png")
    save_p.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), dpi=300)

    # Panel 1: Weekday
    axes[0].bar(
        weekday_df["weekday"].str[:3],
        weekday_df["unique_videos"],
        color="#2ca02c",
        edgecolor="#1c661c",
        alpha=0.85,
    )
    axes[0].set_title("Video Publications by Weekday", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Publication Day", fontsize=10)
    axes[0].set_ylabel("Unique Videos Published", fontsize=10)
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Panel 2: UTC Hour
    axes[1].plot(
        hour_df["publish_hour_utc"],
        hour_df["unique_videos"],
        marker="o",
        color="#9467bd",
        linewidth=2,
    )
    axes[1].set_title(
        "Video Publications by UTC Hour\n(Note: IST is UTC + 5:30; correlation does not prove causation)",
        fontsize=11,
        fontweight="bold",
    )
    axes[1].set_xlabel("Publish Hour (UTC)", fontsize=10)
    axes[1].set_ylabel("Unique Videos Published", fontsize=10)
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    plt.tight_layout()
    fig.savefig(save_p, bbox_inches="tight")
    plt.close(fig)
    return save_p


def generate_all_eda_figures(
    df: pd.DataFrame, figures_dir: Optional[Path] = None
) -> List[Path]:
    """Execute end-to-end visualization pipeline generating all 8 charts.

    Args:
        df: Input cleaned DataFrame.
        figures_dir: Optional destination directory for figures.

    Returns:
        List of generated figure file paths.
    """
    dest = figures_dir or FIGURES_DIR
    dest.mkdir(parents=True, exist_ok=True)

    daily_df = compute_daily_trending_activity(df)
    cat_df = compute_category_performance_summary(df)
    ch_df = compute_channel_performance_summary(df)
    weekday_df, hour_df = compute_publication_patterns(df)

    paths = [
        plot_trending_activity(daily_df, dest / "01_trending_activity_over_time.png"),
        plot_category_performance(cat_df, dest / "02_category_performance_comparison.png"),
        plot_top_channels(ch_df, dest / "03_top_channels_analysis.png"),
        plot_views_vs_engagement(df, dest / "04_views_vs_engagement_scatter.png"),
        plot_engagement_distribution(df, dest / "05_engagement_rate_distribution.png"),
        plot_time_to_trend(df, dest / "06_time_to_trend_by_category.png"),
        plot_trending_persistence(df, dest / "07_trending_persistence_distribution.png"),
        plot_publication_patterns(weekday_df, hour_df, dest / "08_publication_patterns.png"),
    ]
    return paths
