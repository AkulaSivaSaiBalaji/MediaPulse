# MediaPulse — Power BI Analytics Solution Workspace

Welcome to the Power BI reporting module for **MediaPulse — Media Performance & Audience Analytics**.

This directory contains the production-ready Microsoft Power BI reporting assets, semantic model specifications, DAX measure libraries, Power Query M connection scripts, visual build guides, and validation reconciliation matrices.

---

## 1. Directory Structure

```text
powerbi/
├── README.md                                    # Workspace orientation and deployment guide
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

### Opening the Project
1. Open Power BI Desktop.
2. Select **File > Open Report** and choose:
   `D:\MediaPulse\powerbi\MediaPulse_Analytics.pbip`
3. Enter your MySQL database credentials (from `D:\MediaPulse\.env`).
4. Click **Home > Refresh** to populate the in-memory VertiPaq model.

---

## 3. Authoritative Baseline Benchmarks

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
