"""MediaPulse Validated Data Cleaning Pipeline Module.

Implements robust, reproducible data cleaning for the YouTube trending dataset:
- Schema and required column validation.
- Non-overlapping exact row and same-day snapshot deduplication.
- Quarantine of unrecoverable identifiers (#NAME?, #VALUE!).
- Timezone-aware date parsing and time to observed trending computation.
- Category taxonomy enrichment with authoritative fallback.
- Reusable pipeline execution with full data reconciliation.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from src import config, profiling

# Expected standard schema columns
EXPECTED_COLUMNS = [
    "video_id",
    "trending_date",
    "title",
    "channel_title",
    "category_id",
    "publish_time",
    "tags",
    "views",
    "likes",
    "dislikes",
    "comment_count",
    "thumbnail_link",
    "comments_disabled",
    "ratings_disabled",
    "video_error_or_removed",
    "description",
]

# Standard YouTube 11-character base64 URL-safe video ID pattern
YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_schema(
    df: pd.DataFrame, required_columns: Optional[List[str]] = None
) -> Tuple[bool, List[str], List[str]]:
    """Validate DataFrame against required columns and report schema discrepancies.

    Args:
        df: Input DataFrame.
        required_columns: List of column names that must be present.

    Returns:
        Tuple of (is_valid, missing_columns, unexpected_columns).
    """
    req_cols = required_columns or EXPECTED_COLUMNS
    actual_cols = list(df.columns)

    missing = [col for col in req_cols if col not in actual_cols]
    unexpected = [col for col in actual_cols if col not in req_cols]

    is_valid = len(missing) == 0
    return is_valid, missing, unexpected


def detect_invalid_identifiers(
    df: pd.DataFrame, id_column: str = "video_id"
) -> pd.Series:
    """Identify records with invalid or corrupted video identifiers.

    Detects:
    - Microsoft Excel formula export artifacts (#NAME?, #VALUE!).
    - Null, NaN, or whitespace-only identifiers.
    - Non-11-character strings failing YouTube ID regex [A-Za-z0-9_-]{11}.

    Args:
        df: Input DataFrame.
        id_column: Name of the identifier column.

    Returns:
        Boolean Series where True indicates an INVALID identifier.
    """
    if id_column not in df.columns or df.empty:
        return pd.Series(False, index=df.index)

    series_str = df[id_column].fillna("").astype(str).str.strip()

    # Known Excel corruption tokens
    excel_error_mask = series_str.isin(["#NAME?", "#VALUE!", "#REF!", "#N/A"])

    # Regex validation for authentic 11-char YouTube ID
    regex_invalid_mask = ~series_str.str.match(YOUTUBE_VIDEO_ID_REGEX)

    # Empty or null
    empty_mask = series_str == ""

    return excel_error_mask | regex_invalid_mask | empty_mask


def deduplicate_exact_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Remove exact byte-for-byte duplicate rows across all columns.

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of (deduplicated DataFrame, count of duplicate rows removed).
    """
    initial_count = len(df)
    deduped = df.drop_duplicates(keep="first").copy()
    removed = initial_count - len(deduped)
    return deduped, removed


def quarantine_invalid_records(
    df: pd.DataFrame, id_column: str = "video_id"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separate valid records from unrecoverable corrupted identifier records.

    Unrecoverable records (#NAME?, #VALUE!) are quarantined into a separate
    DataFrame for auditing and excluded from video-level entity calculations.

    Args:
        df: Input DataFrame.
        id_column: Identifier column name.

    Returns:
        Tuple of (valid_records_df, quarantined_records_df).
    """
    invalid_mask = detect_invalid_identifiers(df, id_column=id_column)
    quarantined = df[invalid_mask].copy()
    valid = df[~invalid_mask].copy()
    return valid, quarantined


def deduplicate_sameday_snapshots(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    sort_by: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, int]:
    """Deduplicate same-day video snapshots using a deterministic selection rule.

    Does not assume CSV row order represents scrape chronology. Sorts candidate
    snapshots descending by views, likes, and comments to retain the latest and
    most complete observation for that video on that calendar day.

    Args:
        df: Input DataFrame (should contain valid video IDs).
        subset: Composite key columns, defaults to ['video_id', 'trending_date'].
        sort_by: Metric tie-break columns, defaults to ['views', 'likes', 'comment_count'].

    Returns:
        Tuple of (deduplicated DataFrame, count of redundant snapshots removed).
    """
    if df.empty:
        return df.copy(), 0

    sub = subset or ["video_id", "trending_date"]
    sort_cols = sort_by or ["views", "likes", "comment_count"]

    # Verify columns exist before sorting
    available_sort = [col for col in sort_cols if col in df.columns]
    available_sub = [col for col in sub if col in df.columns]

    if not available_sub:
        return df.copy(), 0

    initial_len = len(df)

    # Sort descending on metrics to keep the highest/latest snapshot
    sorted_df = df.sort_values(
        by=available_sub + available_sort,
        ascending=[True] * len(available_sub) + [False] * len(available_sort),
    )

    cleaned = sorted_df.drop_duplicates(subset=available_sub, keep="first").copy()
    # Sort back by original index or deterministic order
    cleaned = cleaned.sort_index()

    removed = initial_len - len(cleaned)
    return cleaned, removed


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing descriptions cleanly without fabricating text.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with imputed descriptions and has_description boolean flag.
    """
    cleaned = df.copy()
    if "description" in cleaned.columns:
        cleaned["has_description"] = cleaned["description"].notnull()
        cleaned["description"] = cleaned["description"].fillna("").astype(str)
    return cleaned


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, extract temporal features, and compute time to observed trending latency.

    - trending_date: parsed from %y.%d.%m to standard ISO date YYYY-MM-DD.
    - publish_time: parsed as UTC datetime.
    - days_to_trend: days elapsed between video publish and trending observation (time to observed trending).

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame enriched with parsed date columns and temporal features.
    """
    cleaned = df.copy()

    if "trending_date" in cleaned.columns:
        cleaned["trending_date_raw"] = cleaned["trending_date"]
        parsed_trending = pd.to_datetime(cleaned["trending_date"], format="%y.%d.%m", errors="coerce")
        cleaned["trending_date"] = parsed_trending.dt.date

    if "publish_time" in cleaned.columns:
        cleaned["publish_time_raw"] = cleaned["publish_time"]
        parsed_publish = pd.to_datetime(cleaned["publish_time"], utc=True, errors="coerce")
        cleaned["publish_datetime_utc"] = parsed_publish
        cleaned["publish_date"] = parsed_publish.dt.date
        cleaned["publish_hour"] = parsed_publish.dt.hour
        cleaned["publish_day_name"] = parsed_publish.dt.day_name()

    # Calculate days between publication and trending (time to observed trending)
    if "trending_date" in cleaned.columns and "publish_date" in cleaned.columns:
        trending_dt = pd.to_datetime(cleaned["trending_date"])
        publish_dt = pd.to_datetime(cleaned["publish_date"])
        cleaned["days_to_trend"] = (trending_dt - publish_dt).dt.days
        # Flag any negative or implausible values (for data quality audit)
        cleaned["is_negative_duration"] = cleaned["days_to_trend"] < 0

    return cleaned


def enrich_categories(
    df: pd.DataFrame, category_map: Optional[Dict[int, str]] = None
) -> pd.DataFrame:
    """Map numeric category_id to human-readable category title.

    Args:
        df: Input DataFrame.
        category_map: Dictionary mapping integer category ID to title string.

    Returns:
        DataFrame with category_title column added.
    """
    cleaned = df.copy()
    mapping = category_map or profiling.load_category_mapping()

    if "category_id" in cleaned.columns:
        cleaned["category_title"] = cleaned["category_id"].map(mapping)
        # Fallback for any unmapped category
        cleaned["category_title"] = cleaned["category_title"].fillna("Unknown Category")

    return cleaned


def audit_negative_values(
    df: pd.DataFrame, columns: Optional[List[str]] = None
) -> Dict[str, int]:
    """Audit numeric columns for negative values prior to clipping or correction.

    Args:
        df: Input DataFrame.
        columns: List of numeric column names to audit (defaults to views, likes, dislikes, comment_count).

    Returns:
        Dictionary mapping column name to the count of negative values found.
    """
    cols = columns or ["views", "likes", "dislikes", "comment_count"]
    negative_counts = {}
    for col in cols:
        if col in df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            negative_counts[col] = int((coerced < 0).sum())
        else:
            negative_counts[col] = 0
    return negative_counts


def validate_numerical_columns(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    return_audit: bool = False,
) -> Any:
    """Audit and validate numeric metric columns to non-negative integers.

    Performs an explicit pre-clipping audit of negative values before applying
    defensive bounding at 0 (lower=0).

    Correction Policy:
        1. Social engagement metrics (views, likes, dislikes, comments) are physical counting
           events and strictly non-negative.
        2. Explicitly audit and count negative values prior to clipping or coercion.
        3. Bound any negative anomalies at 0 via .clip(lower=0) as a defensive pipeline safeguard.
        4. Coerce non-numeric and null entries to 0 and cast to 64-bit integer.

    Args:
        df: Input DataFrame.
        columns: Optional list of numeric columns.
        return_audit: If True, returns tuple of (cleaned_df, negative_audit_counts).

    Returns:
        DataFrame with validated numerical metrics (or tuple with audit dict if return_audit=True).
    """
    cleaned = df.copy()
    metric_cols = columns or ["views", "likes", "dislikes", "comment_count"]
    audit_counts = audit_negative_values(cleaned, columns=metric_cols)

    for col in metric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0).astype(int)
            cleaned[col] = cleaned[col].clip(lower=0)

    if return_audit:
        return cleaned, audit_counts
    return cleaned


def run_cleaning_pipeline(
    raw_csv_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
    output_clean_path: Optional[Path] = None,
    output_quarantine_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute end-to-end data cleaning pipeline with complete reconciliation.

    Pipeline stages:
    1. Schema validation.
    2. Exact row deduplication.
    3. Quarantine of invalid identifiers (#NAME?, #VALUE!).
    4. Deterministic same-day snapshot deduplication on valid records.
    5. Missing value imputation and flag generation.
    6. Date standardization and time to observed trending calculation.
    7. Taxonomy mapping and category enrichment.
    8. Numerical validation with explicit pre-clipping audit and engagement rate calculation.
    9. Artifact export.

    Args:
        raw_csv_path: Optional path to raw CSV file.
        json_path: Optional path to category JSON file.
        output_clean_path: Optional path for cleaned CSV export.
        output_quarantine_path: Optional path for quarantined records export.

    Returns:
        Dictionary containing full data reconciliation metrics and artifact paths.
    """
    csv_p = raw_csv_path or config.get_raw_csv_path()
    json_p = json_path or config.get_raw_json_path()
    clean_p = output_clean_path or (config.DATA_PROCESSED_DIR / "cleaned_youtube_india.csv")
    quarantine_p = output_quarantine_path or (config.DATA_PROCESSED_DIR / "quarantined_records.csv")

    raw_df, cat_map = profiling.load_raw_dataset(csv_p, json_p)
    raw_row_count = len(raw_df)

    # 1. Schema Validation
    is_valid_schema, missing_cols, unexpected_cols = validate_schema(raw_df)
    if not is_valid_schema:
        raise ValueError(f"Schema validation failed. Missing required columns: {missing_cols}")

    # 2. Exact Row Deduplication
    df_deduped, exact_dups_removed = deduplicate_exact_rows(raw_df)

    # 3. Quarantine Invalid Video Identifiers
    valid_df, quarantined_df = quarantine_invalid_records(df_deduped, id_column="video_id")
    quarantined_count = len(quarantined_df)

    # 4. Same-Day Snapshot Deduplication (deterministic selection: highest views/likes/comments)
    clean_valid_df, sameday_dups_removed = deduplicate_sameday_snapshots(valid_df)

    # 5. Missing Values Handling
    clean_valid_df = handle_missing_values(clean_valid_df)
    quarantined_df = handle_missing_values(quarantined_df)

    # 6. Date Processing (Time to Observed Trending)
    clean_valid_df = standardize_dates(clean_valid_df)
    quarantined_df = standardize_dates(quarantined_df)

    # 7. Category Taxonomy Enrichment
    clean_valid_df = enrich_categories(clean_valid_df, category_map=cat_map)
    quarantined_df = enrich_categories(quarantined_df, category_map=cat_map)

    # 8. Numerical Validation with Explicit Pre-Clipping Audit
    clean_valid_df, clean_neg_audit = validate_numerical_columns(clean_valid_df, return_audit=True)
    quarantined_df, quar_neg_audit = validate_numerical_columns(quarantined_df, return_audit=True)

    # Calculate Engagement Rate: (likes + comments) / views * 100
    from src import metrics
    clean_valid_df = metrics.add_engagement_metrics(clean_valid_df)

    # 9. Export Processed Datasets
    clean_p.parent.mkdir(parents=True, exist_ok=True)
    clean_valid_df.to_csv(clean_p, index=False, encoding="utf-8")
    quarantined_df.to_csv(quarantine_p, index=False, encoding="utf-8")

    # Reconciliation Verification:
    # raw_row_count == exact_dups_removed + quarantined_count + sameday_dups_removed + len(clean_valid_df)
    reconciled_sum = exact_dups_removed + quarantined_count + sameday_dups_removed + len(clean_valid_df)
    assert raw_row_count == reconciled_sum, (
        f"Reconciliation error: raw ({raw_row_count}) != sum ({reconciled_sum})"
    )

    return {
        "raw_rows": raw_row_count,
        "exact_duplicates_removed": exact_dups_removed,
        "quarantined_rows": quarantined_count,
        "sameday_duplicates_removed": sameday_dups_removed,
        "cleaned_valid_rows": len(clean_valid_df),
        "reconciled_sum": reconciled_sum,
        "reconciliation_passed": raw_row_count == reconciled_sum,
        "negative_value_audit": clean_neg_audit,
        "unique_valid_videos": int(clean_valid_df["video_id"].nunique()),
        "unique_channels": int(clean_valid_df["channel_title"].nunique()),
        "trending_date_min": str(clean_valid_df["trending_date"].min()),
        "trending_date_max": str(clean_valid_df["trending_date"].max()),
        "missing_descriptions": int((clean_valid_df["description"] == "").sum()),
        "cleaned_file_path": str(clean_p),
        "quarantined_file_path": str(quarantine_p),
    }
