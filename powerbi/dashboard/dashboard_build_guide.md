# MediaPulse — Step-by-Step Power BI Dashboard Build Guide

This guide provides end-to-end instructions for deploying, assembling, and verifying the MediaPulse Power BI reporting solution in Power BI Desktop.

---

## Step 1: Open the Project or Ingest Data

### Option A: Open Native Power BI Project (`.pbip`) — Recommended
1. Launch Power BI Desktop on Windows (`PBIDesktopStore.exe`).
2. Select **File > Open Report**.
3. Navigate to `D:\MediaPulse\powerbi\MediaPulse_Analytics.pbip`.
4. Power BI Desktop automatically loads the complete semantic model (`model.bim`) and report canvas (`report.json`).
5. Click **Home > Refresh** to pull live data from the local MySQL database `mediapulse_db`.

### Option B: Build from Scratch via Power Query M
If starting from a blank PBIX file:
1. Open Power BI Desktop, click **Get Data > MySQL Database**.
2. Server: `127.0.0.1:3306`, Database: `mediapulse_db`.
3. Authentication: Enter database credentials stored in `.env`.
4. In the Navigator window, select the five reporting views:
   - `vw_dim_category`
   - `vw_dim_channel`
   - `vw_dim_video`
   - `vw_fact_trending_snapshots`
   - `vw_dim_date`
5. Click **Transform Data** to open Power Query Editor.
6. Rename the queries to match the star-schema naming:
   - `vw_dim_category` $\rightarrow$ `DimCategory`
   - `vw_dim_channel` $\rightarrow$ `DimChannel`
   - `vw_dim_video` $\rightarrow$ `DimVideo`
   - `vw_fact_trending_snapshots` $\rightarrow$ `FactTrendingSnapshot`
   - `vw_dim_date` $\rightarrow$ `DimDate`
7. Click **Close & Apply**.

---

## Step 2: Configure Model Relationships & Sort-By Columns

1. In the **Model View**, verify the five tables:
   - Link `DimCategory[category_id]` (1) $\rightarrow$ `DimVideo[category_id]` (*) [Single direction].
   - Link `DimChannel[channel_id]` (1) $\rightarrow$ `DimVideo[channel_id]` (*) [Single direction].
   - Link `DimVideo[video_id]` (1) $\rightarrow$ `FactTrendingSnapshot[video_id]` (*) [Single direction].
   - Link `DimDate[full_date]` (1) $\rightarrow$ `FactTrendingSnapshot[trending_date]` (*) [Active, Single].
   - Link `DimDate[full_date]` (1) $\rightarrow$ `DimVideo[publish_date]` (*) [**Inactive**, Single].
2. In the **Data View**, configure chronological sorting for `DimDate`:
   - Select column `month_name` $\rightarrow$ Column Tools $\rightarrow$ **Sort by column** $\rightarrow$ `month_number`.
   - Select column `month_short` $\rightarrow$ Column Tools $\rightarrow$ **Sort by column** $\rightarrow$ `month_number`.
   - Select column `year_month_label` $\rightarrow$ Column Tools $\rightarrow$ **Sort by column** $\rightarrow$ `year_month_sort`.
   - Select column `weekday_name` $\rightarrow$ Column Tools $\rightarrow$ **Sort by column** $\rightarrow$ `iso_weekday_num`.
   - Select column `weekday_short` $\rightarrow$ Column Tools $\rightarrow$ **Sort by column** $\rightarrow$ `iso_weekday_num`.

---

## Step 3: Create Dedicated `_Measures` Table & Add DAX Measures

1. On the **Home** tab, click **Enter Data**.
2. Table Name: `_Measures`, Column Name: `Dummy`. Click **Load**.
3. Create new measures by pasting the expressions from `powerbi/dax/measures.dax`.
4. In Model View, assign each measure to its Display Folder:
   - `01 Core KPIs`
   - `02 Video Performance KPIs`
   - `03 Trending Behavior KPIs`
   - `04 Category & Channel KPIs`
   - `05 Time-Based Analytics`
5. Hide or delete the `Dummy` column. The `_Measures` table will rise to the top with a calculator icon.

---

## Step 4: Construct Report Pages

### Page 1: Executive Overview
1. Rename page to `Executive Overview`.
2. Insert 5 **Card** visuals across the top canvas:
   - Card 1: `[Total Unique Videos]` (Format: Callout size 24pt, bold).
   - Card 2: `[Total Trending Snapshots]`.
   - Card 3: `[Total Channels]`.
   - Card 4: `[Total Categories]`.
   - Card 5: `[Observed Trending Dates]`.
3. Add **Slicers**:
   - Date Slicer: Field `DimDate[full_date]`, Style: Between.
   - Category Slicer: Field `DimCategory[category_title]`, Style: Dropdown.
4. Add **Visual 1 (Daily Trending Activity)**:
   - Visual Type: Line Chart.
   - X-Axis: `DimDate[full_date]`.
   - Y-Axis: `[Daily Trending Snapshot Count]`, `[Rolling 7-Observed-Date Snapshot Average]`.
   - Title: *"Daily Trending Snapshot Volume & 7-Observed-Date Moving Average"*.
5. Add **Visual 2 (Top 10 Categories)**:
   - Visual Type: Clustered Bar Chart (Horizontal).
   - Y-Axis: `DimCategory[category_title]`.
   - X-Axis: `[Total Unique Videos]`.
   - Filter Pane: Top N = 10 by `[Total Unique Videos]`.
6. Add **Visual 3 (Monthly Trending Activity)**:
   - Visual Type: Clustered Column Chart.
   - X-Axis: `DimDate[year_month_label]`.
   - Y-Axis: `[Daily Trending Snapshot Count]`.
   - Tooltips: `[Month-over-Month Snapshot Count Change]`, `[Month-over-Month Snapshot Count Change Percentage]`.

### Page 2: Content & Engagement Analytics
1. Add new page named `Content & Engagement Analytics`.
2. Insert 4 **Card** visuals across the top:
   - `[Median Video-Level Engagement Rate]` (Format: `0.00%`).
   - `[Average Per-Video Peak Views]` (Format: `#,##0`).
   - `[Average Days to First Observed Trending]` (Format: `0.00`).
   - `[Percentage First Observed Trending Within 2 Days]` (Format: `0.00%`).
3. Add **Visual 1 (Category Engagement Benchmark)**:
   - Visual Type: Clustered Bar Chart.
   - Y-Axis: `DimCategory[category_title]`.
   - X-Axis: `[Median Video-Level Engagement Rate]`.
4. Add **Visual 2 (Reach vs Engagement Quadrant)**:
   - Visual Type: Scatter Chart.
   - X-Axis: `[Median Per-Video Peak Views]`.
   - Y-Axis: `[Median Video-Level Engagement Rate]`.
   - Size: `[Total Unique Videos]`.
   - Legend: `DimCategory[category_title]`.
5. Add **Visual 3 (Time to First Observed Trending)**:
   - Visual Type: Clustered Column Chart.
   - X-Axis: Custom conditional column or bins on `DimVideo[days_to_first_trend]` (`0`, `1-2`, `3-7`, `8+`).
   - Y-Axis: `[Total Unique Videos]`.
6. Add **Visual 4 (Publication Weekday Performance)**:
   - Visual Type: Clustered Column Chart.
   - X-Axis: `DimDate[weekday_name]`.
   - Y-Axis: `[Total Unique Videos]`.

### Page 3: Channel Performance
1. Add new page named `Channel Performance`.
2. Insert Top Slicer:
   - Field: `DimChannel[channel_title]` (Search enabled).
3. Add **Visual 1 (Top 15 Channels by Video Count)**:
   - Visual Type: Clustered Bar Chart.
   - Y-Axis: `DimChannel[channel_title]`.
   - X-Axis: `[Total Unique Videos]`.
   - Filter Pane: Top N = 15 by `[Total Unique Videos]`.
4. Add **Visual 2 (Top Channels by Cumulative Peak Reach)**:
   - Visual Type: Clustered Bar Chart.
   - Y-Axis: `DimChannel[channel_title]`.
   - X-Axis: `[Sum of Per-Video Peak Views]`.
   - Filter Pane: Top N = 15 by `[Sum of Per-Video Peak Views]`.
5. Add **Visual 3 (Executive Channel Scorecard Table)**:
   - Visual Type: Table.
   - Columns:
     - `DimChannel[channel_title]`
     - `[Channel Rank by Unique Videos]`
     - `[Total Unique Videos]`
     - `[Sum of Per-Video Peak Views]`
     - `[Average Per-Video Peak Views]`
     - `[Median Video-Level Engagement Rate]`
     - `[Average Distinct Trending Dates per Video]`

---

## Step 5: Verification & Slicer Testing

Follow the verification scenarios in `powerbi/validation/kpi_reconciliation.md` to confirm:
- Slicing by `Entertainment` sets `[Total Unique Videos]` to **7,557**.
- Slicing by `News & Politics` sets `[Total Unique Videos]` to **2,506**.
- Unfiltered `[Total Unique Videos]` is exactly **16,305**.
- Unfiltered `[Sum of Per-Video Peak Views]` is **11,147,625,965**.
- `[Percentage First Observed Trending Within 2 Days]` is **96.41%**.
