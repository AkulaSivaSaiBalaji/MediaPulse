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
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
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
                        "    Data = Source{[Schema=\"mediapulse_db\", Item=\"vw_dim_category\", Kind=\"View\"]}[Data],",
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
                        "    Data = Source{[Schema=\"mediapulse_db\", Item=\"vw_dim_channel\", Kind=\"View\"]}[Data],",
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
                        "    Data = Source{[Schema=\"mediapulse_db\", Item=\"vw_dim_video\", Kind=\"View\"]}[Data],",
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
                        "    Data = Source{[Schema=\"mediapulse_db\", Item=\"vw_fact_trending_snapshots\", Kind=\"View\"]}[Data],",
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
                        "    Data = Source{[Schema=\"mediapulse_db\", Item=\"vw_dim_date\", Kind=\"View\"]}[Data],",
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

# 8. Assemble native modular PBIR report definition (Fabric / Power BI 2.159.883.0+)
DEFINITION_DIR = REPORT_DIR / "definition"
PAGES_DIR = DEFINITION_DIR / "pages"
DEFINITION_DIR.mkdir(parents=True, exist_ok=True)
PAGES_DIR.mkdir(parents=True, exist_ok=True)

def make_measure_field(table_name, measure_name):
    return {
        "field": {
            "Measure": {
                "Expression": {
                    "SourceRef": {
                        "Entity": table_name
                    }
                },
                "Property": measure_name
            }
        },
        "queryRef": f"{table_name}.{measure_name}"
    }

def make_column_field(table_name, column_name):
    return {
        "field": {
            "Column": {
                "Expression": {
                    "SourceRef": {
                        "Entity": table_name
                    }
                },
                "Property": column_name
            }
        },
        "queryRef": f"{table_name}.{column_name}"
    }

# 8.1 definition/version.json
version_payload = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0"
}
(DEFINITION_DIR / "version.json").write_text(json.dumps(version_payload, indent=2), encoding="utf-8")

# 8.2 definition/report.json
report_settings_payload = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
    "themeCollection": {
        "baseTheme": {
            "name": "CY24SU02",
            "reportVersionAtImport": "5.50",
            "type": "SharedResources"
        }
    },
    "layoutOptimization": "None"
}
(DEFINITION_DIR / "report.json").write_text(json.dumps(report_settings_payload, indent=2), encoding="utf-8")

# 8.3 definition/pages/pages.json
pages_metadata = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [
        "ExecutiveOverview",
        "ContentEngagementAnalytics",
        "ChannelPerformance"
    ],
    "activePageName": "ExecutiveOverview"
}
(PAGES_DIR / "pages.json").write_text(json.dumps(pages_metadata, indent=2), encoding="utf-8")

# 8.4 Page 1: Executive Overview
p1_dir = PAGES_DIR / "ExecutiveOverview"
p1_vis_dir = p1_dir / "visuals"
p1_vis_dir.mkdir(parents=True, exist_ok=True)

p1_payload = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
    "name": "ExecutiveOverview",
    "displayName": "Executive Overview",
    "displayOption": "FitToPage",
    "width": 1280,
    "height": 720
}
(p1_dir / "page.json").write_text(json.dumps(p1_payload, indent=2), encoding="utf-8")

p1_visuals = [
    {
        "name": "card_videos",
        "position": {"x": 20, "y": 70, "z": 1000, "width": 230, "height": 90, "tabOrder": 1},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}}
    },
    {
        "name": "card_snapshots",
        "position": {"x": 270, "y": 70, "z": 1001, "width": 230, "height": 90, "tabOrder": 2},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Trending Snapshots")]}}
    },
    {
        "name": "card_channels",
        "position": {"x": 520, "y": 70, "z": 1002, "width": 230, "height": 90, "tabOrder": 3},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Channels")]}}
    },
    {
        "name": "card_categories",
        "position": {"x": 770, "y": 70, "z": 1003, "width": 230, "height": 90, "tabOrder": 4},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Categories")]}}
    },
    {
        "name": "card_dates",
        "position": {"x": 1020, "y": 70, "z": 1004, "width": 240, "height": 90, "tabOrder": 5},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Observed Trending Dates")]}}
    },
    {
        "name": "line_daily_trending",
        "position": {"x": 20, "y": 180, "z": 1005, "width": 780, "height": 260, "tabOrder": 6},
        "visualType": "lineChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimDate", "full_date")]},
            "Y": {"projections": [
                make_measure_field("_Measures", "Daily Trending Snapshot Count"),
                make_measure_field("_Measures", "Rolling 7-Observed-Date Snapshot Average")
            ]}
        }
    },
    {
        "name": "bar_top_categories",
        "position": {"x": 820, "y": 180, "z": 1006, "width": 440, "height": 260, "tabOrder": 7},
        "visualType": "clusteredBarChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimCategory", "category_title")]},
            "Y": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}
        }
    },
    {
        "name": "col_monthly_trending",
        "position": {"x": 20, "y": 460, "z": 1007, "width": 780, "height": 240, "tabOrder": 8},
        "visualType": "clusteredColumnChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimDate", "year_month_label")]},
            "Y": {"projections": [make_measure_field("_Measures", "Daily Trending Snapshot Count")]}
        }
    },
    {
        "name": "card_coverage_audit",
        "position": {"x": 820, "y": 460, "z": 1008, "width": 440, "height": 240, "tabOrder": 9},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Observed Trending Dates")]}}
    }
]

for v in p1_visuals:
    v_dir = p1_vis_dir / v["name"]
    v_dir.mkdir(parents=True, exist_ok=True)
    v_payload = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": v["name"],
        "position": v["position"],
        "visual": {
            "visualType": v["visualType"],
            "query": {
                "queryState": v["queryState"]
            }
        }
    }
    (v_dir / "visual.json").write_text(json.dumps(v_payload, indent=2), encoding="utf-8")

# 8.5 Page 2: Content & Engagement Analytics
p2_dir = PAGES_DIR / "ContentEngagementAnalytics"
p2_vis_dir = p2_dir / "visuals"
p2_vis_dir.mkdir(parents=True, exist_ok=True)

p2_payload = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
    "name": "ContentEngagementAnalytics",
    "displayName": "Content & Engagement Analytics",
    "displayOption": "FitToPage",
    "width": 1280,
    "height": 720
}
(p2_dir / "page.json").write_text(json.dumps(p2_payload, indent=2), encoding="utf-8")

p2_visuals = [
    {
        "name": "card_median_er",
        "position": {"x": 20, "y": 70, "z": 1000, "width": 290, "height": 90, "tabOrder": 1},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Median Video-Level Engagement Rate")]}}
    },
    {
        "name": "card_avg_peak_views",
        "position": {"x": 330, "y": 70, "z": 1001, "width": 290, "height": 90, "tabOrder": 2},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Average Per-Video Peak Views")]}}
    },
    {
        "name": "card_avg_latency",
        "position": {"x": 640, "y": 70, "z": 1002, "width": 290, "height": 90, "tabOrder": 3},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Average Days to First Observed Trending")]}}
    },
    {
        "name": "card_pct_le2",
        "position": {"x": 950, "y": 70, "z": 1003, "width": 310, "height": 90, "tabOrder": 4},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Percentage First Observed Trending Within 2 Days")]}}
    },
    {
        "name": "bar_category_er",
        "position": {"x": 20, "y": 180, "z": 1004, "width": 600, "height": 250, "tabOrder": 5},
        "visualType": "clusteredBarChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimCategory", "category_title")]},
            "Y": {"projections": [make_measure_field("_Measures", "Median Video-Level Engagement Rate")]}
        }
    },
    {
        "name": "scatter_reach_er",
        "position": {"x": 640, "y": 180, "z": 1005, "width": 620, "height": 250, "tabOrder": 6},
        "visualType": "scatterChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimCategory", "category_title")]},
            "X": {"projections": [make_measure_field("_Measures", "Median Per-Video Peak Views")]},
            "Y": {"projections": [make_measure_field("_Measures", "Median Video-Level Engagement Rate")]},
            "Size": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}
        }
    },
    {
        "name": "col_weekday_volume",
        "position": {"x": 20, "y": 450, "z": 1006, "width": 600, "height": 250, "tabOrder": 7},
        "visualType": "clusteredColumnChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimDate", "weekday_name")]},
            "Y": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}
        }
    },
    {
        "name": "col_hour_volume",
        "position": {"x": 640, "y": 450, "z": 1007, "width": 620, "height": 250, "tabOrder": 8},
        "visualType": "clusteredColumnChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimVideo", "publish_hour")]},
            "Y": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}
        }
    }
]

for v in p2_visuals:
    v_dir = p2_vis_dir / v["name"]
    v_dir.mkdir(parents=True, exist_ok=True)
    v_payload = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": v["name"],
        "position": v["position"],
        "visual": {
            "visualType": v["visualType"],
            "query": {
                "queryState": v["queryState"]
            }
        }
    }
    (v_dir / "visual.json").write_text(json.dumps(v_payload, indent=2), encoding="utf-8")

# 8.6 Page 3: Channel Performance
p3_dir = PAGES_DIR / "ChannelPerformance"
p3_vis_dir = p3_dir / "visuals"
p3_vis_dir.mkdir(parents=True, exist_ok=True)

p3_payload = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
    "name": "ChannelPerformance",
    "displayName": "Channel Performance",
    "displayOption": "FitToPage",
    "width": 1280,
    "height": 720
}
(p3_dir / "page.json").write_text(json.dumps(p3_payload, indent=2), encoding="utf-8")

p3_visuals = [
    {
        "name": "card_ch_total",
        "position": {"x": 20, "y": 70, "z": 1000, "width": 290, "height": 90, "tabOrder": 1},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Channels")]}}
    },
    {
        "name": "card_ch_videos",
        "position": {"x": 330, "y": 70, "z": 1001, "width": 290, "height": 90, "tabOrder": 2},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}}
    },
    {
        "name": "card_ch_reach",
        "position": {"x": 640, "y": 70, "z": 1002, "width": 290, "height": 90, "tabOrder": 3},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Sum of Per-Video Peak Views")]}}
    },
    {
        "name": "card_ch_er",
        "position": {"x": 950, "y": 70, "z": 1003, "width": 310, "height": 90, "tabOrder": 4},
        "visualType": "card",
        "queryState": {"Values": {"projections": [make_measure_field("_Measures", "Median Video-Level Engagement Rate")]}}
    },
    {
        "name": "bar_top_channels_videos",
        "position": {"x": 20, "y": 180, "z": 1004, "width": 600, "height": 250, "tabOrder": 5},
        "visualType": "clusteredBarChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimChannel", "channel_title")]},
            "Y": {"projections": [make_measure_field("_Measures", "Total Unique Videos")]}
        }
    },
    {
        "name": "bar_top_channels_reach",
        "position": {"x": 640, "y": 180, "z": 1005, "width": 620, "height": 250, "tabOrder": 6},
        "visualType": "clusteredBarChart",
        "queryState": {
            "Category": {"projections": [make_column_field("DimChannel", "channel_title")]},
            "Y": {"projections": [make_measure_field("_Measures", "Sum of Per-Video Peak Views")]}
        }
    },
    {
        "name": "table_channel_scorecard",
        "position": {"x": 20, "y": 450, "z": 1006, "width": 1240, "height": 250, "tabOrder": 7},
        "visualType": "tableEx",
        "queryState": {
            "Values": {
                "projections": [
                    make_column_field("DimChannel", "channel_title"),
                    make_measure_field("_Measures", "Channel Rank by Unique Videos"),
                    make_measure_field("_Measures", "Total Unique Videos"),
                    make_measure_field("_Measures", "Sum of Per-Video Peak Views"),
                    make_measure_field("_Measures", "Average Per-Video Peak Views"),
                    make_measure_field("_Measures", "Median Video-Level Engagement Rate"),
                    make_measure_field("_Measures", "Average Distinct Trending Dates per Video")
                ]
            }
        }
    }
]

for v in p3_visuals:
    v_dir = p3_vis_dir / v["name"]
    v_dir.mkdir(parents=True, exist_ok=True)
    v_payload = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json",
        "name": v["name"],
        "position": v["position"],
        "visual": {
            "visualType": v["visualType"],
            "query": {
                "queryState": v["queryState"]
            }
        }
    }
    (v_dir / "visual.json").write_text(json.dumps(v_payload, indent=2), encoding="utf-8")

# 8.7 Remove old monolithic report.json if present at REPORT_DIR root
old_report_json = REPORT_DIR / "report.json"
if old_report_json.exists():
    old_report_json.unlink()
    print("Removed legacy monolithic report.json from root of .Report")

print("Power BI Project (PBIP) generated successfully at:", PBI_DIR)
