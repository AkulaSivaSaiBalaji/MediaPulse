# MediaPulse — Power BI Analytics Solution Workspace

Welcome to the Power BI reporting module for **MediaPulse — Media Performance & Audience Analytics**.

This directory contains the production-ready Microsoft Power BI reporting assets, semantic model specifications, DAX measure libraries, Power Query M connection scripts, visual build guides, and validation reconciliation matrices.

---

## 1. Directory Structure

```text
powerbi/
├── README.md                                    # Workspace orientation and deployment guide
├── build_powerbi_project.py                     # Deterministic PBIP project generator
├── MediaPulse_Analytics.pbip                     # Root Power BI Project file (Open with Power BI Desktop)
├── MediaPulse_Analytics.Report/                 # Power BI Report Project definition
│   ├── definition.pbir                         # Semantic model pointer
│   └── report.json                             # 3-page canvas layouts, cards, charts, and slicers
├── MediaPulse_Analytics.SemanticModel/          # Power BI Semantic Model definition
│   ├── definition.pbism                        # Semantic model manifest
│   └── model.bim                               # Tabular Object Model (TOM) JSON schema
├── model/
│   ├── semantic_model_specification.md         # Star-schema design, storage mode, and grain
│   ├── relationships.md                        # Cardinalities, filter directions, role-playing date
│   └── data_dictionary.md                      # Complete column specifications and data types
├── dax/
│   ├── measures.dax                            # 27 production DAX measures across 5 display folders
│   └── dax_explanations.md                     # Mathematical derivations and filter context logic
├── powerquery/
│   └── mysql_import_queries.pq                 # Power Query M scripts for MySQL 8.0 views
├── dashboard/
│   ├── dashboard_design_specification.md       # Visual styling, 16:9 canvas grids, palette
│   └── dashboard_build_guide.md                # Step-by-step visual assembly walkthrough
└── validation/
    └── kpi_reconciliation.md                   # 10 multi-grain reconciliation scenarios
```

---

## 2. Quick Start: Opening the Report

### Prerequisites
1. **Power BI Desktop:** Installed on Windows (`PBIDesktopStore.exe` or standard installer).
2. **MySQL Server 8.0:** Running locally on port `3306` with database `mediapulse_db` initialized.
3. **MySQL Connector/NET (or ODBC Driver):** Standard Oracle MySQL ADO.NET connector.

> [!WARNING]
> **Desktop GUI & Live DAX Engine Verification Status:**  
> Power BI Desktop GUI visual rendering, interactive slicer cross-filtering behavior, and native VertiPaq DAX engine execution have **not yet been verified in the live Power BI Desktop application** due to running within a headless non-interactive terminal environment.  
> All semantic model files (`model.bim`), 27 DAX measures (`measures.dax`), report canvas specifications (`report.json`), and Power Query M queries have been validated programmatically and tested via automated pytest suites against MySQL 8.0.

### Opening the Project
1. Open Power BI Desktop.
2. Select **File > Open Report** and choose:
   `D:\MediaPulse\powerbi\MediaPulse_Analytics.pbip`
3. Enter your MySQL database credentials (from `D:\MediaPulse\.env`).
4. Click **Home > Refresh** to populate the in-memory VertiPaq model.

---

## 3. Remaining Manual Power BI Desktop Validation Steps

Upon opening `MediaPulse_Analytics.pbip` in Power BI Desktop, the analyst should execute the following checklist:

1. **Semantic Model Load:** Confirm all 5 tables (`_Measures`, `DimCategory`, `DimChannel`, `DimVideo`, `FactTrendingSnapshot`, `DimDate`) appear in the Model View with single-direction 1-to-many relationships intact.
2. **Data Refresh:** Run `Home > Refresh` and confirm all tables pull data from MySQL views without schema or credential errors.
3. **Canvas Visual Rendering:** Review all 4 report pages:
   - *Page 1 (Executive Overview):* Verify Top KPI cards, daily snapshot activity line chart, top 10 categories bar chart, and monthly volume column chart.
   - *Page 2 (Content & Engagement Analytics):* Verify median ER baseline (0.83%), scatter plot (peak views vs. ER), velocity distribution, and upload hour charts.
   - *Page 3 (Channel Performance):* Verify channel rankings, portfolio category diversification stacked bar, and executive channel scorecard table.
   - *Page 4 (Methodology & Quality Audit):* Verify KPI reconciliation matrix and collection coverage audit card (205 observed dates).
4. **Slicer Interaction & DAX Engine Test:**
   - Select a specific category (e.g. `Entertainment`) and verify cards and visual totals update dynamically.
   - Select a specific date or date range and verify `[Sum of Per-Video Peak Views]` correctly switches from all-time `SUM(DimVideo[peak_views])` to windowed `SUMX(VALUES(FactTrendingSnapshot[video_id]), CALCULATE(MAX(views)))`.
   - Verify unobserved dates (e.g. `2018-04-10`) display blank cards with zero bleed.

---

## 4. Authoritative Baseline Benchmarks

All calculations have been cross-reconciled against MySQL 8.0 and Pandas in `tests/test_powerbi_metrics.py`:

- **Total Unique Videos:** **16,305**
- **Total Trending Snapshots:** **32,265**
- **Total Publishing Channels:** **1,423**
- **Total Content Categories:** **17**
- **Observed Trending Dates:** **205** (out of 213 calendar days)
- **Cumulative Peak Views:** **11,147,625,965 views**
- **Average Peak Views:** **683,693.71 views**
- **Median Peak Views:** **205,619.00 views**
- **Median Video Engagement Rate:** **0.8284%**
- **Average Velocity (Days to Trend):** **1.31 days** (Median = **1.0 day**)
- **Same-Day Trending Videos:** **420 videos** (**2.58%**)
- **Videos First Trending $\le 2$ Days:** **15,720 videos** (**96.41%**)
- **Average Trending Persistence:** **1.98 distinct snapshot dates**
