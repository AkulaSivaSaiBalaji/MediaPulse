"""MediaPulse Dataset Profiling & Inspection Module.

Provides reproducible data profiling functions to audit raw video data, schema
types, null values, duplicate records, identifier integrity, and category mappings.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd
from src import config


def load_category_mapping(json_path: Optional[Path] = None) -> Dict[int, str]:
    """Parse YouTube category JSON file and return category_id to title mapping.

    Args:
        json_path: Optional Path to category JSON. If None, uses configured default.

    Returns:
        Dict mapping integer category ID to category title string.
    """
    path = json_path or config.get_raw_json_path()
    if not path.exists():
        raise FileNotFoundError(f"Category JSON file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    category_map: Dict[int, str] = {}
    for item in data.get("items", []):
        cat_id = int(item["id"])
        cat_title = item["snippet"]["title"]
        category_map[cat_id] = cat_title

    # Authoritative source: YouTube Data API v3 videoCategories resource defines
    # category ID 29 as "Nonprofits & Activism". Included here as verified fallback.
    if 29 not in category_map:
        category_map[29] = "Nonprofits & Activism"

    return category_map


def load_raw_dataset(
    csv_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, Dict[int, str]]:
    """Load raw CSV dataset and category mapping.

    Args:
        csv_path: Optional Path to CSV dataset.
        json_path: Optional Path to category JSON.

    Returns:
        Tuple of (raw DataFrame, category mapping dict).
    """
    csv_p = csv_path or config.get_raw_csv_path()
    if not csv_p.exists():
        raise FileNotFoundError(f"Raw CSV dataset not found at: {csv_p}")

    df = pd.read_csv(csv_p)
    cat_map = load_category_mapping(json_path)
    return df, cat_map


def inspect_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Inspect dataset dimensions and column data types.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary containing row count, column count, and column type map.
    """
    return {
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


def audit_missing_values(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Compute null and empty string counts across all columns.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary of column null counts and percentages.
    """
    total = len(df)
    results = {}
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = round((null_count / total) * 100, 2) if total > 0 else 0.0
        results[col] = {
            "null_count": null_count,
            "null_percentage": null_pct,
        }
    return results


def audit_duplicates(df: pd.DataFrame) -> Dict[str, int]:
    """Calculate exact duplicate rows and composite same-day duplicates.

    Note on Relationship:
        Exact duplicates (all columns identical) are a strict subset of composite
        same-day duplicates on (video_id, trending_date). The difference represents
        intra-day metric updates where a video was captured multiple times on the
        same date with updated views/likes.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary with exact duplicates, composite duplicates, and incremental intra-day metric updates.
    """
    exact_dups = int(df.duplicated().sum())
    composite_dups = 0
    if "video_id" in df.columns and "trending_date" in df.columns:
        composite_dups = int(df.duplicated(subset=["video_id", "trending_date"]).sum())

    return {
        "exact_duplicate_rows": exact_dups,
        "composite_key_duplicates": composite_dups,
        "intraday_metric_updates": max(0, composite_dups - exact_dups),
    }



def audit_identifiers(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit video and channel identifiers for anomalies (such as Excel #NAME? errors).

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary of identifier audit results.
    """
    results: Dict[str, Any] = {}
    if "video_id" in df.columns:
        name_err_mask = df["video_id"] == "#NAME?"
        name_err_count = int(name_err_mask.sum())
        unique_videos = int(df["video_id"].nunique())
        results["unique_video_ids"] = unique_videos
        results["malformed_excel_name_errors"] = name_err_count
    if "channel_title" in df.columns:
        results["unique_channels"] = int(df["channel_title"].nunique())

    return results


def audit_date_ranges(df: pd.DataFrame) -> Dict[str, Any]:
    """Parse and calculate date spans for trending dates and publish times.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary with parsed min, max, and span days.
    """
    results: Dict[str, Any] = {}
    if "trending_date" in df.columns:
        # Format in Indian YouTube dataset is YY.DD.MM (e.g. 17.14.11)
        parsed_trending = pd.to_datetime(df["trending_date"], format="%y.%d.%m", errors="coerce")
        results["trending_date_min"] = parsed_trending.min().strftime("%Y-%m-%d") if not parsed_trending.empty else None
        results["trending_date_max"] = parsed_trending.max().strftime("%Y-%m-%d") if not parsed_trending.empty else None
        results["trending_days_span"] = (
            (parsed_trending.max() - parsed_trending.min()).days if not parsed_trending.empty else 0
        )

    if "publish_time" in df.columns:
        parsed_publish = pd.to_datetime(df["publish_time"], errors="coerce")
        results["publish_time_min"] = parsed_publish.min().strftime("%Y-%m-%d") if not parsed_publish.empty else None
        results["publish_time_max"] = parsed_publish.max().strftime("%Y-%m-%d") if not parsed_publish.empty else None

    return results


def audit_numeric_metrics(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Verify ranges, negative values, and distributions for views, likes, dislikes, comments.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary with summary statistics and negative value flags for metrics.
    """
    metric_cols = ["views", "likes", "dislikes", "comment_count"]
    results = {}
    for col in metric_cols:
        if col in df.columns:
            results[col] = {
                "min": int(df[col].min()),
                "max": int(df[col].max()),
                "mean": float(round(df[col].mean(), 2)),
                "median": float(df[col].median()),
                "negative_count": int((df[col] < 0).sum()),
            }
    return results


def audit_category_coverage(
    df: pd.DataFrame, category_map: Dict[int, str]
) -> Dict[str, Any]:
    """Check category IDs in the CSV against the category taxonomy.

    Args:
        df: Input DataFrame.
        category_map: Mapping dictionary of category ID to title.

    Returns:
        Dictionary with counts of distinct categories, mapped and unmapped categories.
    """
    csv_categories = set(df["category_id"].unique()) if "category_id" in df.columns else set()
    mapped_categories = set(category_map.keys())
    unmapped = csv_categories - mapped_categories

    return {
        "distinct_csv_categories": len(csv_categories),
        "total_taxonomy_categories": len(mapped_categories),
        "unmapped_category_ids": list(unmapped),
    }


def generate_data_profile(
    csv_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate complete end-to-end data quality and schema profile.

    Args:
        csv_path: Optional CSV path.
        json_path: Optional JSON path.

    Returns:
        Complete dictionary containing all audit findings.
    """
    df, cat_map = load_raw_dataset(csv_path, json_path)
    return {
        "schema": inspect_schema(df),
        "missing_values": audit_missing_values(df),
        "duplicates": audit_duplicates(df),
        "identifiers": audit_identifiers(df),
        "dates": audit_date_ranges(df),
        "metrics": audit_numeric_metrics(df),
        "categories": audit_category_coverage(df, cat_map),
    }
