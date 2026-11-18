// ==============================================================================
// MediaPulse — Media Performance & Audience Analytics
// Power Query M Scripts for Power BI Import Mode
// Target: MySQL 8.0 (mediapulse_db) via Native MySQL Connector
// ==============================================================================

// ------------------------------------------------------------------------------
// Parameter: ServerName
// Type: Text, Default: "localhost:3306" or "127.0.0.1:3306"
// ------------------------------------------------------------------------------
let
    ServerName = "127.0.0.1:3306" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
in
    ServerName

// ------------------------------------------------------------------------------
// Parameter: DatabaseName
// Type: Text, Default: "mediapulse_db"
// ------------------------------------------------------------------------------
let
    DatabaseName = "mediapulse_db" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
in
    DatabaseName


// ------------------------------------------------------------------------------
// Table: DimCategory
// Source: vw_dim_category
// Grain: 1 row per unique category (17 rows)
// ------------------------------------------------------------------------------
let
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true]),
    ViewData = Source{[Schema=DatabaseName, Item="vw_dim_category", Kind="View"]}[Data],
    TypedTable = Table.TransformColumnTypes(ViewData,{
        {"category_id", Int64.Type},
        {"category_title", type text},
        {"ingested_at", type datetime}
    })
in
    TypedTable


// ------------------------------------------------------------------------------
// Table: DimChannel
// Source: vw_dim_channel
// Grain: 1 row per unique publisher channel (1,423 rows)
// Note: Preserves case-variant channels under utf8mb4_bin collation.
// ------------------------------------------------------------------------------
let
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true]),
    ViewData = Source{[Schema=DatabaseName, Item="vw_dim_channel", Kind="View"]}[Data],
    TypedTable = Table.TransformColumnTypes(ViewData,{
        {"channel_id", Int64.Type},
        {"channel_title", type text},
        {"ingested_at", type datetime}
    })
in
    TypedTable


// ------------------------------------------------------------------------------
// Table: DimVideo
// Source: vw_dim_video
// Grain: 1 row per unique creative video asset (16,305 rows)
// Architecture: Pre-aggregates video-level lifetime peak reach and latency to
// eliminate expensive nested table iterators in DAX while preserving star-schema integrity.
// ------------------------------------------------------------------------------
let
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true]),
    ViewData = Source{[Schema=DatabaseName, Item="vw_dim_video", Kind="View"]}[Data],
    TypedTable = Table.TransformColumnTypes(ViewData,{
        {"video_id", type text},
        {"channel_id", Int64.Type},
        {"category_id", Int64.Type},
        {"video_title", type text},
        {"publish_time", type datetime},
        {"publish_date", type date},
        {"publish_hour", Int64.Type},
        {"publish_day_name", type text},
        {"thumbnail_link", type text},
        {"has_description", type logical},
        {"comments_disabled_earliest", type logical},
        {"ratings_disabled_earliest", type logical},
        {"video_error_or_removed_earliest", type logical},
        {"first_trending_date", type date},
        {"last_trending_date", type date},
        {"distinct_trending_days", Int64.Type},
        {"days_to_first_trend", Int64.Type},
        {"peak_views", Int64.Type},
        {"peak_likes", Int64.Type},
        {"peak_dislikes", Int64.Type},
        {"peak_comments", Int64.Type},
        {"lifetime_engagement_rate", type number},
        {"is_same_day_trending", Int64.Type},
        {"is_trending_within_2days", Int64.Type}
    })
in
    TypedTable


// ------------------------------------------------------------------------------
// Table: FactTrendingSnapshot
// Source: vw_fact_trending_snapshots
// Grain: 1 row per daily snapshot observation (32,265 rows)
// ------------------------------------------------------------------------------
let
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true]),
    ViewData = Source{[Schema=DatabaseName, Item="vw_fact_trending_snapshots", Kind="View"]}[Data],
    TypedTable = Table.TransformColumnTypes(ViewData,{
        {"snapshot_id", Int64.Type},
        {"video_id", type text},
        {"trending_date", type date},
        {"views", Int64.Type},
        {"likes", Int64.Type},
        {"dislikes", Int64.Type},
        {"comment_count", Int64.Type},
        {"comments_disabled", type logical},
        {"ratings_disabled", type logical},
        {"video_error_or_removed", type logical},
        {"snapshot_days_to_trend", Int64.Type},
        {"snapshot_engagement_rate", type number},
        {"snapshot_total_interaction_rate", type number},
        {"snapshot_like_ratio", type number},
        {"snapshot_ingested_at", type datetime}
    })
in
    TypedTable


// ------------------------------------------------------------------------------
// Table: DimDate
// Source: vw_dim_date
// Grain: 1 row per calendar day (426 dates: 2017-05-01 to 2018-06-30)
// Role: Chronological calendar table with sort-by columns configured.
// ------------------------------------------------------------------------------
let
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true]),
    ViewData = Source{[Schema=DatabaseName, Item="vw_dim_date", Kind="View"]}[Data],
    TypedTable = Table.TransformColumnTypes(ViewData,{
        {"full_date", type date},
        {"calendar_year", Int64.Type},
        {"month_number", Int64.Type},
        {"month_name", type text},
        {"month_short", type text},
        {"year_month_label", type text},
        {"year_month_sort", Int64.Type},
        {"quarter_name", type text},
        {"iso_week_number", Int64.Type},
        {"day_of_week_num", Int64.Type},
        {"iso_weekday_num", Int64.Type},
        {"weekday_name", type text},
        {"weekday_short", type text},
        {"is_trending_snapshot_date", Int64.Type}
    })
in
    TypedTable
