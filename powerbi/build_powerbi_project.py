"""Script to generate the complete Power BI Project (.pbip) for MediaPulse."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name in ('scratch', 'powerbi') else Path(__file__).resolve().parent
PBI_DIR = BASE_DIR / "powerbi"
REPORT_DIR = PBI_DIR / "MediaPulse_Analytics.Report"
MODEL_DIR = PBI_DIR / "MediaPulse_Analytics.SemanticModel"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# 1. MediaPulse_Analytics.pbip
pbip_payload = {
    "version": "1.0",
    "artifacts": [
        {
            "report": {
                "path": "MediaPulse_Analytics.Report"
            }
        }
    ],
    "settings": {
        "enableAutoRecovery": True
    }
}
(PBI_DIR / "MediaPulse_Analytics.pbip").write_text(json.dumps(pbip_payload, indent=2), encoding="utf-8")

# 2. MediaPulse_Analytics.Report/definition.pbir
pbir_payload = {
    "version": "4.0",
    "datasetReference": {
        "byPath": {
            "path": "../MediaPulse_Analytics.SemanticModel"
        },
        "byConnection": None
    }
}
(REPORT_DIR / "definition.pbir").write_text(json.dumps(pbir_payload, indent=2), encoding="utf-8")

# 3. MediaPulse_Analytics.SemanticModel/definition.pbism
pbism_payload = {
    "version": "4.0",
    "settings": {}
}
(MODEL_DIR / "definition.pbism").write_text(json.dumps(pbism_payload, indent=2), encoding="utf-8")

# 4. Construct Measures for model.bim
measures = [
    # Group 1: Core KPIs
    {
        "name": "Total Unique Videos",
        "expression": "IF(ISCROSSFILTERED(DimDate), DISTINCTCOUNT(FactTrendingSnapshot[video_id]), DISTINCTCOUNT(DimVideo[video_id]))",
        "formatString": "#,##0",
        "displayFolder": "01 Core KPIs",
        "description": "Authoritative count of unique creative assets observed trending (Baseline: 16,305 all-time; dynamically evaluates observed video count under date filters)."
    },
    {
        "name": "Total Trending Snapshots",
        "expression": "COUNTROWS(FactTrendingSnapshot)",
        "formatString": "#,##0",
        "displayFolder": "01 Core KPIs",
        "description": "Total daily trending observation snapshots across the temporal window (Baseline: 32,265)."
    },
    {
        "name": "Total Channels",
        "expression": "DISTINCTCOUNT(DimChannel[channel_id])",
        "formatString": "#,##0",
        "displayFolder": "01 Core KPIs",
        "description": "Total unique YouTube publishers with at least one trending video (Baseline: 1,423)."
    },
    {
        "name": "Total Categories",
        "expression": "DISTINCTCOUNT(DimCategory[category_id])",
        "formatString": "#,##0",
        "displayFolder": "01 Core KPIs",
        "description": "Total distinct YouTube content categories represented (Baseline: 17)."
    },
    {
        "name": "Observed Trending Dates",
        "expression": "CALCULATE(DISTINCTCOUNT(FactTrendingSnapshot[trending_date]), FactTrendingSnapshot[trending_date] <> BLANK())",
        "formatString": "#,##0",
        "displayFolder": "01 Core KPIs",
        "description": "Count of distinct calendar dates with collected trending snapshots (Baseline: 205)."
    },
    # Group 2: Video Performance KPIs
    {
        "name": "Sum of Per-Video Peak Views",
        "expression": (
            "IF(\n"
            "    ISCROSSFILTERED(DimDate),\n"
            "    SUMX(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[views]))),\n"
            "    SUM(DimVideo[peak_views])\n"
            ")"
        ),
        "formatString": "#,##0",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Sum of Per-Video Peak Cumulative Views. Evaluates maximum views per creative asset, preventing snapshot accumulation duplication (Baseline: 11,147,625,965). Does not represent unduplicated human audience reach."
    },
    {
        "name": "Average Per-Video Peak Views",
        "expression": "DIVIDE([Sum of Per-Video Peak Views], [Total Unique Videos], 0)",
        "formatString": "#,##0.00",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Arithmetic mean per-video peak cumulative views per unique creative asset (Baseline: 683,693.71)."
    },
    {
        "name": "Median Per-Video Peak Views",
        "expression": (
            "IF(\n"
            "    ISCROSSFILTERED(DimDate),\n"
            "    MEDIANX(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[views]))),\n"
            "    MEDIAN(DimVideo[peak_views])\n"
            ")"
        ),
        "formatString": "#,##0",
        "displayFolder": "02 Video Performance KPIs",
        "description": "True 50th percentile peak cumulative views, robust against extreme viral blockbuster skew (Baseline: 205,619.00)."
    },
    {
        "name": "Video Peak Likes",
        "expression": "IF(ISCROSSFILTERED(DimDate), SUMX(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[likes]))), SUM(DimVideo[peak_likes]))",
        "formatString": "#,##0",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Cumulative sum of per-video maximum observed likes."
    },
    {
        "name": "Video Peak Comments",
        "expression": "IF(ISCROSSFILTERED(DimDate), SUMX(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[comment_count]))), SUM(DimVideo[peak_comments]))",
        "formatString": "#,##0",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Cumulative sum of per-video maximum observed comments."
    },
    {
        "name": "Catalog-Level Engagement Rate",
        "expression": "DIVIDE([Video Peak Likes] + [Video Peak Comments], [Sum of Per-Video Peak Views], 0) * 100",
        "formatString": "0.0000\"%\"",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Macro portfolio engagement: total peak interactions divided by total peak cumulative views times 100."
    },
    {
        "name": "Average Video-Level Engagement Rate",
        "expression": (
            "IF(\n"
            "    ISCROSSFILTERED(DimDate),\n"
            "    AVERAGEX(\n"
            "        FILTER(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[views])) > 0),\n"
            "        CALCULATE(DIVIDE(MAX(FactTrendingSnapshot[likes]) + MAX(FactTrendingSnapshot[comment_count]), MAX(FactTrendingSnapshot[views]), 0) * 100)\n"
            "    ),\n"
            "    AVERAGEX(FILTER(DimVideo, DimVideo[peak_views] > 0), DimVideo[lifetime_engagement_rate])\n"
            ")"
        ),
        "formatString": "0.0000\"%\"",
        "displayFolder": "02 Video Performance KPIs",
        "description": "Arithmetic mean of individual creative asset engagement rates (Baseline: 2.0579%)."
    },
    {
        "name": "Median Video-Level Engagement Rate",
        "expression": (
            "IF(\n"
            "    ISCROSSFILTERED(DimDate),\n"
            "    MEDIANX(\n"
            "        FILTER(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(FactTrendingSnapshot[views])) > 0),\n"
            "        CALCULATE(DIVIDE(MAX(FactTrendingSnapshot[likes]) + MAX(FactTrendingSnapshot[comment_count]), MAX(FactTrendingSnapshot[views]), 0) * 100)\n"
            "    ),\n"
            "    MEDIANX(FILTER(DimVideo, DimVideo[peak_views] > 0), DimVideo[lifetime_engagement_rate])\n"
            ")"
        ),
        "formatString": "0.0000\"%\"",
        "displayFolder": "02 Video Performance KPIs",
        "description": "True median engagement intensity across unique videos, robust against low-denominator outliers (Baseline: 0.8284%)."
    },
    # Group 3: Trending Behavior KPIs
    {
        "name": "Average Days to First Observed Trending",
        "expression": "AVERAGEX(DimVideo, DimVideo[days_to_first_trend])",
        "formatString": "0.00",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Mean elapsed calendar days between video publication and earliest observed trending appearance (Baseline: 1.31 days)."
    },
    {
        "name": "Median Days to First Observed Trending",
        "expression": "MEDIANX(DimVideo, DimVideo[days_to_first_trend])",
        "formatString": "0.0",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Median elapsed calendar days to earliest observed trending appearance (Baseline: 1.0 day)."
    },
    {
        "name": "Same-Day Trending Videos",
        "expression": "CALCULATE([Total Unique Videos], DimVideo[is_same_day_trending] = 1)",
        "formatString": "#,##0",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Unique videos appearing on the trending list on their calendar publication date (Day 0) (Baseline: 420 videos)."
    },
    {
        "name": "Videos First Observed Trending Within 2 Days",
        "expression": "CALCULATE([Total Unique Videos], DimVideo[is_trending_within_2days] = 1)",
        "formatString": "#,##0",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Unique videos appearing on trending within 48 hours of upload (Day 0, 1, or 2) (Baseline: 15,720 videos)."
    },
    {
        "name": "Percentage First Observed Trending Within 2 Days",
        "expression": "DIVIDE([Videos First Observed Trending Within 2 Days], [Total Unique Videos], 0) * 100",
        "formatString": "0.00\"%\"",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Share of unique videos appearing on trending within 2 calendar days of upload (Baseline: 96.41%)."
    },
    {
        "name": "Average Distinct Trending Dates per Video",
        "expression": "AVERAGEX(DimVideo, DimVideo[distinct_trending_days])",
        "formatString": "0.00",
        "displayFolder": "03 Trending Behavior KPIs",
        "description": "Average number of distinct snapshot dates videos were observed on the trending list (Baseline: 1.98 days). Represents observed trending persistence across snapshots, not continuous uninterrupted feed retention."
    },
    # Group 4: Category and Channel KPIs
    {
        "name": "Category Share of Unique Videos",
        "expression": "DIVIDE([Total Unique Videos], CALCULATE([Total Unique Videos], ALLSELECTED(DimCategory)), 0) * 100",
        "formatString": "0.00\"%\"",
        "displayFolder": "04 Category & Channel KPIs",
        "description": "Percentage contribution of unique videos from the active category within current slicer scope."
    },
    {
        "name": "Channel Share of Unique Videos",
        "expression": "DIVIDE([Total Unique Videos], CALCULATE([Total Unique Videos], ALLSELECTED(DimChannel)), 0) * 100",
        "formatString": "0.00\"%\"",
        "displayFolder": "04 Category & Channel KPIs",
        "description": "Percentage contribution of unique videos from the active channel within current slicer scope."
    },
    {
        "name": "Category Rank by Unique Videos",
        "expression": "IF(ISINSCOPE(DimCategory[category_title]), RANKX(ALLSELECTED(DimCategory), [Total Unique Videos], , DESC, Dense))",
        "formatString": "0",
        "displayFolder": "04 Category & Channel KPIs",
        "description": "Dense rank of categories based on catalog unique video count."
    },
    {
        "name": "Channel Rank by Unique Videos",
        "expression": "IF(ISINSCOPE(DimChannel[channel_title]), RANKX(ALLSELECTED(DimChannel), [Total Unique Videos], , DESC, Dense))",
        "formatString": "0",
        "displayFolder": "04 Category & Channel KPIs",
        "description": "Dense rank of publisher channels based on catalog unique video count."
    },
    # Group 5: Time-Based Analytics
    {
        "name": "Daily Trending Snapshot Count",
        "expression": "COUNTROWS(FactTrendingSnapshot)",
        "formatString": "#,##0",
        "displayFolder": "05 Time-Based Analytics",
        "description": "Total daily trending snapshots recorded for the selected date or period."
    },
    {
        "name": "Month-over-Month Snapshot Count Change",
        "expression": (
            "VAR CurrentMonthSnapshots = [Daily Trending Snapshot Count]\n"
            "VAR PreviousMonthSnapshots = CALCULATE([Daily Trending Snapshot Count], DATEADD(DimDate[full_date], -1, MONTH))\n"
            "RETURN IF(NOT ISBLANK(CurrentMonthSnapshots) && NOT ISBLANK(PreviousMonthSnapshots), CurrentMonthSnapshots - PreviousMonthSnapshots, BLANK())"
        ),
        "formatString": "+#,##0;-#,##0;0",
        "displayFolder": "05 Time-Based Analytics",
        "description": "Absolute change in snapshot observations compared to the prior calendar month."
    },
    {
        "name": "Month-over-Month Snapshot Count Change Percentage",
        "expression": (
            "VAR CurrentMonthSnapshots = [Daily Trending Snapshot Count]\n"
            "VAR PreviousMonthSnapshots = CALCULATE([Daily Trending Snapshot Count], DATEADD(DimDate[full_date], -1, MONTH))\n"
            "RETURN DIVIDE(CurrentMonthSnapshots - PreviousMonthSnapshots, PreviousMonthSnapshots, 0) * 100"
        ),
        "formatString": "+0.00\"%\";-0.00\"%\";0.00\"%\"",
        "displayFolder": "05 Time-Based Analytics",
        "description": "Percentage change in snapshot observations compared to the prior calendar month."
    },
    {
        "name": "Rolling 7-Observed-Date Snapshot Average",
        "expression": (
            "VAR CurrentDate = MAX(DimDate[full_date])\n"
            "VAR Last7ObservedDates = TOPN(7, FILTER(ALL(DimDate), DimDate[full_date] <= CurrentDate && DimDate[is_trending_snapshot_date] = 1), DimDate[full_date], DESC)\n"
            "RETURN IF(MAX(DimDate[is_trending_snapshot_date]) = 1, AVERAGEX(Last7ObservedDates, CALCULATE([Daily Trending Snapshot Count])))"
        ),
        "formatString": "#,##0.0",
        "displayFolder": "05 Time-Based Analytics",
        "description": "7-observed-date moving average of snapshot volume. Strictly bridges missing collection dates."
    }
]

# 5. Construct Tables for model.bim
tables = [
    # Table 0: _Measures
    {
        "name": "_Measures",
        "columns": [
            {
                "name": "Measure_ID",
                "dataType": "int64",
                "isHidden": True,
                "sourceColumn": "Measure_ID"
            }
        ],
        "partitions": [
            {
                "name": "_Measures-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = Table.FromRows(Json.Document(Binary.Decompress(Binary.FromText(\"i45WMlSKjQUA\", BinaryEncoding.Base64), Compression.Deflate)), let _t = ((type nullable text) meta [Serialized.Text = true]) in type table [Measure_ID = _t]),",
                        "    #\"Changed Type\" = Table.TransformColumnTypes(Source,{{\"Measure_ID\", Int64.Type}})",
                        "in",
                        "    #\"Changed Type\""
                    ]
                }
            }
        ],
        "measures": measures
    },
    # Table 1: DimCategory
    {
        "name": "DimCategory",
        "columns": [
            {"name": "category_id", "dataType": "int64", "sourceColumn": "category_id", "isKey": True},
            {"name": "category_title", "dataType": "string", "sourceColumn": "category_title"},
            {"name": "ingested_at", "dataType": "dateTime", "sourceColumn": "ingested_at"}
        ],
        "partitions": [
            {
                "name": "DimCategory-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = MySQL.Database(\"127.0.0.1:3306\", \"mediapulse_db\", [ReturnSingleDatabase=true]),",
                        "    Data = Source{[Schema=\"mediapulse_db\"]}[Data]{[Name=\"vw_dim_category\"]}[Data],",
                        "    Typed = Table.TransformColumnTypes(Data, {{\"category_id\", Int64.Type}, {\"category_title\", type text}, {\"ingested_at\", type datetime}})",
                        "in",
                        "    Typed"
                    ]
                }
            }
        ]
    },
    # Table 2: DimChannel
    {
        "name": "DimChannel",
        "columns": [
            {"name": "channel_id", "dataType": "int64", "sourceColumn": "channel_id", "isKey": True},
            {"name": "channel_title", "dataType": "string", "sourceColumn": "channel_title"},
            {"name": "ingested_at", "dataType": "dateTime", "sourceColumn": "ingested_at"}
        ],
        "partitions": [
            {
                "name": "DimChannel-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = MySQL.Database(\"127.0.0.1:3306\", \"mediapulse_db\", [ReturnSingleDatabase=true]),",
                        "    Data = Source{[Schema=\"mediapulse_db\"]}[Data]{[Name=\"vw_dim_channel\"]}[Data],",
                        "    Typed = Table.TransformColumnTypes(Data, {{\"channel_id\", Int64.Type}, {\"channel_title\", type text}, {\"ingested_at\", type datetime}})",
                        "in",
                        "    Typed"
                    ]
                }
            }
        ]
    },
    # Table 3: DimVideo
    {
        "name": "DimVideo",
        "columns": [
            {"name": "video_id", "dataType": "string", "sourceColumn": "video_id", "isKey": True},
            {"name": "channel_id", "dataType": "int64", "sourceColumn": "channel_id"},
            {"name": "category_id", "dataType": "int64", "sourceColumn": "category_id"},
            {"name": "video_title", "dataType": "string", "sourceColumn": "video_title"},
            {"name": "publish_time", "dataType": "dateTime", "sourceColumn": "publish_time"},
            {"name": "publish_date", "dataType": "dateTime", "sourceColumn": "publish_date"},
            {"name": "publish_hour", "dataType": "int64", "sourceColumn": "publish_hour"},
            {"name": "publish_day_name", "dataType": "string", "sourceColumn": "publish_day_name"},
            {"name": "thumbnail_link", "dataType": "string", "sourceColumn": "thumbnail_link"},
            {"name": "has_description", "dataType": "boolean", "sourceColumn": "has_description"},
            {"name": "comments_disabled_earliest", "dataType": "boolean", "sourceColumn": "comments_disabled_earliest"},
            {"name": "ratings_disabled_earliest", "dataType": "boolean", "sourceColumn": "ratings_disabled_earliest"},
            {"name": "video_error_or_removed_earliest", "dataType": "boolean", "sourceColumn": "video_error_or_removed_earliest"},
            {"name": "first_trending_date", "dataType": "dateTime", "sourceColumn": "first_trending_date"},
            {"name": "last_trending_date", "dataType": "dateTime", "sourceColumn": "last_trending_date"},
            {"name": "distinct_trending_days", "dataType": "int64", "sourceColumn": "distinct_trending_days"},
            {"name": "days_to_first_trend", "dataType": "int64", "sourceColumn": "days_to_first_trend"},
            {"name": "peak_views", "dataType": "int64", "sourceColumn": "peak_views"},
            {"name": "peak_likes", "dataType": "int64", "sourceColumn": "peak_likes"},
            {"name": "peak_dislikes", "dataType": "int64", "sourceColumn": "peak_dislikes"},
            {"name": "peak_comments", "dataType": "int64", "sourceColumn": "peak_comments"},
            {"name": "lifetime_engagement_rate", "dataType": "double", "sourceColumn": "lifetime_engagement_rate"},
            {"name": "is_same_day_trending", "dataType": "int64", "sourceColumn": "is_same_day_trending"},
            {"name": "is_trending_within_2days", "dataType": "int64", "sourceColumn": "is_trending_within_2days"}
        ],
        "partitions": [
            {
                "name": "DimVideo-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = MySQL.Database(\"127.0.0.1:3306\", \"mediapulse_db\", [ReturnSingleDatabase=true]),",
                        "    Data = Source{[Schema=\"mediapulse_db\"]}[Data]{[Name=\"vw_dim_video\"]}[Data],",
                        "    Typed = Table.TransformColumnTypes(Data, {",
                        "        {\"video_id\", type text}, {\"channel_id\", Int64.Type}, {\"category_id\", Int64.Type},",
                        "        {\"video_title\", type text}, {\"publish_time\", type datetime}, {\"publish_date\", type date},",
                        "        {\"publish_hour\", Int64.Type}, {\"publish_day_name\", type text}, {\"thumbnail_link\", type text},",
                        "        {\"has_description\", type logical}, {\"comments_disabled_earliest\", type logical},",
                        "        {\"ratings_disabled_earliest\", type logical}, {\"video_error_or_removed_earliest\", type logical},",
                        "        {\"first_trending_date\", type date}, {\"last_trending_date\", type date},",
                        "        {\"distinct_trending_days\", Int64.Type}, {\"days_to_first_trend\", Int64.Type},",
                        "        {\"peak_views\", Int64.Type}, {\"peak_likes\", Int64.Type}, {\"peak_dislikes\", Int64.Type},",
                        "        {\"peak_comments\", Int64.Type}, {\"lifetime_engagement_rate\", type number},",
                        "        {\"is_same_day_trending\", Int64.Type}, {\"is_trending_within_2days\", Int64.Type}",
                        "    })",
                        "in",
                        "    Typed"
                    ]
                }
            }
        ]
    },
    # Table 4: FactTrendingSnapshot
    {
        "name": "FactTrendingSnapshot",
        "columns": [
            {"name": "snapshot_id", "dataType": "int64", "sourceColumn": "snapshot_id", "isKey": True},
            {"name": "video_id", "dataType": "string", "sourceColumn": "video_id"},
            {"name": "trending_date", "dataType": "dateTime", "sourceColumn": "trending_date"},
            {"name": "views", "dataType": "int64", "sourceColumn": "views"},
            {"name": "likes", "dataType": "int64", "sourceColumn": "likes"},
            {"name": "dislikes", "dataType": "int64", "sourceColumn": "dislikes"},
            {"name": "comment_count", "dataType": "int64", "sourceColumn": "comment_count"},
            {"name": "comments_disabled", "dataType": "boolean", "sourceColumn": "comments_disabled"},
            {"name": "ratings_disabled", "dataType": "boolean", "sourceColumn": "ratings_disabled"},
            {"name": "video_error_or_removed", "dataType": "boolean", "sourceColumn": "video_error_or_removed"},
            {"name": "snapshot_days_to_trend", "dataType": "int64", "sourceColumn": "snapshot_days_to_trend"},
            {"name": "snapshot_engagement_rate", "dataType": "double", "sourceColumn": "snapshot_engagement_rate"},
            {"name": "snapshot_total_interaction_rate", "dataType": "double", "sourceColumn": "snapshot_total_interaction_rate"},
            {"name": "snapshot_like_ratio", "dataType": "double", "sourceColumn": "snapshot_like_ratio"},
            {"name": "snapshot_ingested_at", "dataType": "dateTime", "sourceColumn": "snapshot_ingested_at"}
        ],
        "partitions": [
            {
                "name": "FactTrendingSnapshot-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = MySQL.Database(\"127.0.0.1:3306\", \"mediapulse_db\", [ReturnSingleDatabase=true]),",
                        "    Data = Source{[Schema=\"mediapulse_db\"]}[Data]{[Name=\"vw_fact_trending_snapshots\"]}[Data],",
                        "    Typed = Table.TransformColumnTypes(Data, {",
                        "        {\"snapshot_id\", Int64.Type}, {\"video_id\", type text}, {\"trending_date\", type date},",
                        "        {\"views\", Int64.Type}, {\"likes\", Int64.Type}, {\"dislikes\", Int64.Type}, {\"comment_count\", Int64.Type},",
                        "        {\"comments_disabled\", type logical}, {\"ratings_disabled\", type logical}, {\"video_error_or_removed\", type logical},",
                        "        {\"snapshot_days_to_trend\", Int64.Type}, {\"snapshot_engagement_rate\", type number},",
                        "        {\"snapshot_total_interaction_rate\", type number}, {\"snapshot_like_ratio\", type number},",
                        "        {\"snapshot_ingested_at\", type datetime}",
                        "    })",
                        "in",
                        "    Typed"
                    ]
                }
            }
        ]
    },
    # Table 5: DimDate
    {
        "name": "DimDate",
        "columns": [
            {"name": "full_date", "dataType": "dateTime", "sourceColumn": "full_date", "isKey": True},
            {"name": "calendar_year", "dataType": "int64", "sourceColumn": "calendar_year"},
            {"name": "month_number", "dataType": "int64", "sourceColumn": "month_number"},
            {"name": "month_name", "dataType": "string", "sourceColumn": "month_name", "sortByColumn": "month_number"},
            {"name": "month_short", "dataType": "string", "sourceColumn": "month_short", "sortByColumn": "month_number"},
            {"name": "year_month_label", "dataType": "string", "sourceColumn": "year_month_label", "sortByColumn": "year_month_sort"},
            {"name": "year_month_sort", "dataType": "int64", "sourceColumn": "year_month_sort"},
            {"name": "quarter_name", "dataType": "string", "sourceColumn": "quarter_name"},
            {"name": "iso_week_number", "dataType": "int64", "sourceColumn": "iso_week_number"},
            {"name": "day_of_week_num", "dataType": "int64", "sourceColumn": "day_of_week_num"},
            {"name": "iso_weekday_num", "dataType": "int64", "sourceColumn": "iso_weekday_num"},
            {"name": "weekday_name", "dataType": "string", "sourceColumn": "weekday_name", "sortByColumn": "iso_weekday_num"},
            {"name": "weekday_short", "dataType": "string", "sourceColumn": "weekday_short", "sortByColumn": "iso_weekday_num"},
            {"name": "is_trending_snapshot_date", "dataType": "int64", "sourceColumn": "is_trending_snapshot_date"}
        ],
        "partitions": [
            {
                "name": "DimDate-Partition",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        "    Source = MySQL.Database(\"127.0.0.1:3306\", \"mediapulse_db\", [ReturnSingleDatabase=true]),",
                        "    Data = Source{[Schema=\"mediapulse_db\"]}[Data]{[Name=\"vw_dim_date\"]}[Data],",
                        "    Typed = Table.TransformColumnTypes(Data, {",
                        "        {\"full_date\", type date}, {\"calendar_year\", Int64.Type}, {\"month_number\", Int64.Type},",
                        "        {\"month_name\", type text}, {\"month_short\", type text}, {\"year_month_label\", type text},",
                        "        {\"year_month_sort\", Int64.Type}, {\"quarter_name\", type text}, {\"iso_week_number\", Int64.Type},",
                        "        {\"day_of_week_num\", Int64.Type}, {\"iso_weekday_num\", Int64.Type}, {\"weekday_name\", type text},",
                        "        {\"weekday_short\", type text}, {\"is_trending_snapshot_date\", Int64.Type}",
                        "    })",
                        "in",
                        "    Typed"
                    ]
                }
            }
        ]
    }
]

# 6. Construct Relationships for model.bim
relationships = [
    {
        "name": "DimCategory_DimVideo_category_id",
        "fromTable": "DimVideo",
        "fromColumn": "category_id",
        "toTable": "DimCategory",
        "toColumn": "category_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True
    },
    {
        "name": "DimChannel_DimVideo_channel_id",
        "fromTable": "DimVideo",
        "fromColumn": "channel_id",
        "toTable": "DimChannel",
        "toColumn": "channel_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True
    },
    {
        "name": "DimVideo_FactTrendingSnapshot_video_id",
        "fromTable": "FactTrendingSnapshot",
        "fromColumn": "video_id",
        "toTable": "DimVideo",
        "toColumn": "video_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True
    },
    {
        "name": "DimDate_FactTrendingSnapshot_trending_date",
        "fromTable": "FactTrendingSnapshot",
        "fromColumn": "trending_date",
        "toTable": "DimDate",
        "toColumn": "full_date",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True
    },
    {
        "name": "DimDate_DimVideo_publish_date",
        "fromTable": "DimVideo",
        "fromColumn": "publish_date",
        "toTable": "DimDate",
        "toColumn": "full_date",
        "crossFilteringBehavior": "oneDirection",
        "isActive": False
    }
]

# 7. Assemble model.bim payload
model_bim = {
    "name": "MediaPulse_Analytics",
    "compatibilityLevel": 1550,
    "model": {
        "culture": "en-US",
        "dataAccessOptions": {
            "legacyRedirects": True,
            "fastCombine": False
        },
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "sourceQueryCulture": "en-US",
        "tables": tables,
        "relationships": relationships,
        "annotations": [
            {"name": "PBI_QueryOrder", "value": "[\"DimCategory\",\"DimChannel\",\"DimVideo\",\"FactTrendingSnapshot\",\"DimDate\",\"_Measures\"]"},
            {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}
        ]
    }
}

(MODEL_DIR / "model.bim").write_text(json.dumps(model_bim, indent=2), encoding="utf-8")

# 8. Assemble report.json for MediaPulse_Analytics.Report
report_json = {
    "config": json.dumps({
        "version": "5.50",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU02",
                "version": "5.50",
                "type": 2
            }
        },
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True
    }),
    "layoutOptimization": 0,
    "sections": [
        # Page 1: Executive Overview
        {
            "name": "ExecutiveOverview",
            "displayName": "Executive Overview",
            "filters": "[]",
            "ordinal": 0,
            "width": 1280,
            "height": 720,
            "visualContainers": [
                # Card 1: Unique Videos
                {
                    "x": 20, "y": 70, "z": 1, "width": 230, "height": 90,
                    "config": json.dumps({
                        "name": "card_videos",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Unique Videos"}]},
                            "prototypeQuery": {"Select": [{"Measure": {"Property": "Total Unique Videos"}, "Name": "_Measures.Total Unique Videos"}]}
                        }
                    })
                },
                # Card 2: Snapshots
                {
                    "x": 270, "y": 70, "z": 2, "width": 230, "height": 90,
                    "config": json.dumps({
                        "name": "card_snapshots",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Trending Snapshots"}]},
                            "prototypeQuery": {"Select": [{"Measure": {"Property": "Total Trending Snapshots"}, "Name": "_Measures.Total Trending Snapshots"}]}
                        }
                    })
                },
                # Card 3: Channels
                {
                    "x": 520, "y": 70, "z": 3, "width": 230, "height": 90,
                    "config": json.dumps({
                        "name": "card_channels",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Channels"}]},
                            "prototypeQuery": {"Select": [{"Measure": {"Property": "Total Channels"}, "Name": "_Measures.Total Channels"}]}
                        }
                    })
                },
                # Card 4: Categories
                {
                    "x": 770, "y": 70, "z": 4, "width": 230, "height": 90,
                    "config": json.dumps({
                        "name": "card_categories",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Categories"}]},
                            "prototypeQuery": {"Select": [{"Measure": {"Property": "Total Categories"}, "Name": "_Measures.Total Categories"}]}
                        }
                    })
                },
                # Card 5: Observed Dates
                {
                    "x": 1020, "y": 70, "z": 5, "width": 240, "height": 90,
                    "config": json.dumps({
                        "name": "card_dates",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Observed Trending Dates"}]},
                            "prototypeQuery": {"Select": [{"Measure": {"Property": "Observed Trending Dates"}, "Name": "_Measures.Observed Trending Dates"}]}
                        }
                    })
                },
                # Visual 1: Daily Trending Snapshot Activity (Line Chart)
                {
                    "x": 20, "y": 180, "z": 6, "width": 780, "height": 260,
                    "config": json.dumps({
                        "name": "line_daily_trending",
                        "singleVisual": {
                            "visualType": "lineChart",
                            "projections": {
                                "Category": [{"queryRef": "DimDate.full_date"}],
                                "Y": [
                                    {"queryRef": "_Measures.Daily Trending Snapshot Count"},
                                    {"queryRef": "_Measures.Rolling 7-Observed-Date Snapshot Average"}
                                ]
                            }
                        }
                    })
                },
                # Visual 2: Top 10 Categories by Unique Videos (Bar Chart)
                {
                    "x": 820, "y": 180, "z": 7, "width": 440, "height": 260,
                    "config": json.dumps({
                        "name": "bar_top_categories",
                        "singleVisual": {
                            "visualType": "clusteredBarChart",
                            "projections": {
                                "Category": [{"queryRef": "DimCategory.category_title"}],
                                "Y": [{"queryRef": "_Measures.Total Unique Videos"}]
                            }
                        }
                    })
                },
                # Visual 3: Monthly Observed Trending Activity (Column Chart)
                {
                    "x": 20, "y": 460, "z": 8, "width": 780, "height": 240,
                    "config": json.dumps({
                        "name": "col_monthly_trending",
                        "singleVisual": {
                            "visualType": "clusteredColumnChart",
                            "projections": {
                                "Category": [{"queryRef": "DimDate.year_month_label"}],
                                "Y": [{"queryRef": "_Measures.Daily Trending Snapshot Count"}]
                            }
                        }
                    })
                },
                # Visual 4: Coverage Callout Card
                {
                    "x": 820, "y": 460, "z": 9, "width": 440, "height": 240,
                    "config": json.dumps({
                        "name": "textbox_coverage",
                        "singleVisual": {
                            "visualType": "textbox"
                        }
                    })
                }
            ]
        },
        # Page 2: Content & Engagement Analytics
        {
            "name": "ContentEngagementAnalytics",
            "displayName": "Content & Engagement Analytics",
            "filters": "[]",
            "ordinal": 1,
            "width": 1280,
            "height": 720,
            "visualContainers": [
                # Card 1: Median ER
                {
                    "x": 20, "y": 70, "z": 1, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_median_er",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Median Video-Level Engagement Rate"}]}
                        }
                    })
                },
                # Card 2: Average Peak Views
                {
                    "x": 330, "y": 70, "z": 2, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_avg_peak_views",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Average Per-Video Peak Views"}]}
                        }
                    })
                },
                # Card 3: Average Latency
                {
                    "x": 640, "y": 70, "z": 3, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_avg_latency",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Average Days to First Observed Trending"}]}
                        }
                    })
                },
                # Card 4: % Within 2 Days
                {
                    "x": 950, "y": 70, "z": 4, "width": 310, "height": 90,
                    "config": json.dumps({
                        "name": "card_pct_le2",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Percentage First Observed Trending Within 2 Days"}]}
                        }
                    })
                },
                # Visual 1: Category vs Median Engagement Rate
                {
                    "x": 20, "y": 180, "z": 5, "width": 600, "height": 250,
                    "config": json.dumps({
                        "name": "bar_category_er",
                        "singleVisual": {
                            "visualType": "clusteredBarChart",
                            "projections": {
                                "Category": [{"queryRef": "DimCategory.category_title"}],
                                "Y": [{"queryRef": "_Measures.Median Video-Level Engagement Rate"}]
                            }
                        }
                    })
                },
                # Visual 2: Reach vs Engagement Scatter Plot
                {
                    "x": 640, "y": 180, "z": 6, "width": 620, "height": 250,
                    "config": json.dumps({
                        "name": "scatter_reach_er",
                        "singleVisual": {
                            "visualType": "scatterChart",
                            "projections": {
                                "Category": [{"queryRef": "DimCategory.category_title"}],
                                "X": [{"queryRef": "_Measures.Median Per-Video Peak Views"}],
                                "Y": [{"queryRef": "_Measures.Median Video-Level Engagement Rate"}],
                                "Size": [{"queryRef": "_Measures.Total Unique Videos"}]
                            }
                        }
                    })
                },
                # Visual 3: Publication Weekday Performance
                {
                    "x": 20, "y": 450, "z": 7, "width": 600, "height": 250,
                    "config": json.dumps({
                        "name": "col_weekday_volume",
                        "singleVisual": {
                            "visualType": "clusteredColumnChart",
                            "projections": {
                                "Category": [{"queryRef": "DimDate.weekday_name"}],
                                "Y": [{"queryRef": "_Measures.Total Unique Videos"}]
                            }
                        }
                    })
                },
                # Visual 4: Publication Hour Distribution
                {
                    "x": 640, "y": 450, "z": 8, "width": 620, "height": 250,
                    "config": json.dumps({
                        "name": "col_hour_volume",
                        "singleVisual": {
                            "visualType": "clusteredColumnChart",
                            "projections": {
                                "Category": [{"queryRef": "DimVideo.publish_hour"}],
                                "Y": [{"queryRef": "_Measures.Total Unique Videos"}]
                            }
                        }
                    })
                }
            ]
        },
        # Page 3: Channel Performance
        {
            "name": "ChannelPerformance",
            "displayName": "Channel Performance",
            "filters": "[]",
            "ordinal": 2,
            "width": 1280,
            "height": 720,
            "visualContainers": [
                # Card 1: Total Channels
                {
                    "x": 20, "y": 70, "z": 1, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_ch_total",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Channels"}]}
                        }
                    })
                },
                # Card 2: Selected Channel Videos
                {
                    "x": 330, "y": 70, "z": 2, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_ch_videos",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Total Unique Videos"}]}
                        }
                    })
                },
                # Card 3: Selected Channel Peak Reach
                {
                    "x": 640, "y": 70, "z": 3, "width": 290, "height": 90,
                    "config": json.dumps({
                        "name": "card_ch_reach",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Sum of Per-Video Peak Views"}]}
                        }
                    })
                },
                # Card 4: Selected Channel Median ER
                {
                    "x": 950, "y": 70, "z": 4, "width": 310, "height": 90,
                    "config": json.dumps({
                        "name": "card_ch_er",
                        "singleVisual": {
                            "visualType": "card",
                            "projections": {"Fields": [{"queryRef": "_Measures.Median Video-Level Engagement Rate"}]}
                        }
                    })
                },
                # Visual 1: Top 15 Channels by Unique Videos
                {
                    "x": 20, "y": 180, "z": 5, "width": 600, "height": 250,
                    "config": json.dumps({
                        "name": "bar_top_channels_videos",
                        "singleVisual": {
                            "visualType": "clusteredBarChart",
                            "projections": {
                                "Category": [{"queryRef": "DimChannel.channel_title"}],
                                "Y": [{"queryRef": "_Measures.Total Unique Videos"}]
                            }
                        }
                    })
                },
                # Visual 2: Top Channels by Cumulative Peak Views
                {
                    "x": 640, "y": 180, "z": 6, "width": 620, "height": 250,
                    "config": json.dumps({
                        "name": "bar_top_channels_reach",
                        "singleVisual": {
                            "visualType": "clusteredBarChart",
                            "projections": {
                                "Category": [{"queryRef": "DimChannel.channel_title"}],
                                "Y": [{"queryRef": "_Measures.Sum of Per-Video Peak Views"}]
                            }
                        }
                    })
                },
                # Visual 3: Channel Executive Scorecard Table
                {
                    "x": 20, "y": 450, "z": 7, "width": 1240, "height": 250,
                    "config": json.dumps({
                        "name": "table_channel_scorecard",
                        "singleVisual": {
                            "visualType": "tableEx",
                            "projections": {
                                "Values": [
                                    {"queryRef": "DimChannel.channel_title"},
                                    {"queryRef": "_Measures.Channel Rank by Unique Videos"},
                                    {"queryRef": "_Measures.Total Unique Videos"},
                                    {"queryRef": "_Measures.Sum of Per-Video Peak Views"},
                                    {"queryRef": "_Measures.Average Per-Video Peak Views"},
                                    {"queryRef": "_Measures.Median Video-Level Engagement Rate"},
                                    {"queryRef": "_Measures.Average Distinct Trending Dates per Video"}
                                ]
                            }
                        }
                    })
                }
            ]
        }
    ]
}

(REPORT_DIR / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")

print("Power BI Project (PBIP) generated successfully at:", PBI_DIR)
