# MediaPulse — Media Performance & Audience Analytics

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-MySQL%208-orange.svg)](https://www.mysql.com/)
[![BI](https://img.shields.io/badge/BI-Power%20BI-yellow.svg)](https://powerbi.microsoft.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end media analytics and business intelligence project engineered to analyze trending video dynamics, audience engagement patterns, category distributions, and creator retention across digital video platforms.

Developed as a production-grade portfolio project tailored for the **Wipro Analyst L1 (Business Analyst / Data Analyst - Media)** role (Job ID: 218535).

---

## 1. Project Overview

Digital media platforms generate massive volumes of continuous interaction data. Understanding what drives content to trend, how engagement rates vary across categories, and how audience sentiment translates into longevity is critical for media executives, content strategists, and advertising planners.

**MediaPulse** provides:
- Automated data ingestion, validation, and cleaning pipelines.
- Rigorous exploratory data analysis (EDA) with publication-quality visualizations.
- Relational data modeling in MySQL 8 (3NF/Star Schema hybrid) supporting idempotent pipelines.
- Advanced SQL analytics using window functions, CTEs, and cohort aggregations.
- Interactive Power BI executive dashboards backed by DAX measures.
- Data-driven business recommendations for digital content creators and media planners.

---

## 2. Technology Stack

- **Programming & Scripting:** Python 3.12.10
- **Data Engineering & Analysis:** Pandas, NumPy
- **Data Visualization:** Matplotlib, Seaborn
- **Database & ORM:** MySQL 8, SQLAlchemy, PyMySQL, mysql-connector-python
- **Business Intelligence:** Power BI Desktop (DAX, Data Modeling)
- **Quality Assurance & Testing:** pytest
- **Environment & Configuration:** python-dotenv
- **Version Control & Repository:** Git, GitHub (`https://github.com/AkulaSivaSaiBalaji/MediaPulse`)

---

## 3. Dataset Attribution

Primary Dataset: **YouTube Trending Video Dataset**  
Source: [Kaggle — YouTube Trending Video Dataset (by Rishav Sharma)](https://www.kaggle.com/datasets/rsrishav/youtube-trending-video-dataset)  
Target Region: **India (IN)**  
Primary Source Files:
- `IN_youtube_trending_data.csv` — Daily trending video observations
- `IN_category_id.json` — Category ID to category title mappings

---

## 4. Project Architecture & Directory Structure

```text
MediaPulse/
├── data/
│   ├── raw/               # Raw immutable datasets (e.g., IN_youtube_trending_data.csv)
│   └── processed/         # Cleaned, validated, and normalized parquet/csv datasets
├── notebooks/             # Structured Jupyter notebooks for EDA and profiling
│   ├── 01_data_inspection.ipynb
│   ├── 02_data_cleaning.ipynb
│   └── 03_exploratory_analysis.ipynb
├── src/                   # Production modular Python package
│   ├── __init__.py
│   ├── config.py          # Centralized configuration and path management
│   ├── ingestion.py       # Data loading and schema validation
│   ├── cleaning.py        # Cleaning, deduplication, and transformation logic
│   ├── metrics.py         # Business KPI calculation engine
│   ├── database.py        # MySQL connection and idempotent ingestion
│   └── visualization.py   # Publication-standard plotting routines
├── sql/                   # Database schemas and analytical queries
│   ├── schema.sql         # Table definitions, constraints, indexes
│   ├── analysis_queries.sql # Window functions, CTEs, aggregations
│   └── views.sql          # Analytical views for Power BI / reporting
├── dashboard/             # Power BI assets and documentation
│   ├── dax_measures.md    # Formal DAX calculations and business logic
│   └── dashboard_guide.md # Dashboard build, layout, and UX guide
├── reports/               # Executive briefings and analytical documentation
│   ├── data_quality_report.md
│   └── business_insights.md
├── tests/                 # Automated pytest test suite
│   ├── __init__.py
│   ├── test_smoke.py      # Environment and path smoke tests
│   ├── test_cleaning.py   # Pipeline transformation tests
│   ├── test_metrics.py    # KPI verification tests
│   └── test_database.py   # MySQL schema and ingestion tests
├── .env.example           # Template for environment variables
├── .gitignore             # Comprehensive ignore rules
├── requirements.txt       # Production dependencies
└── README.md              # Project documentation
```

---

## 5. Getting Started

### Prerequisites
- Python 3.12+
- Git
- MySQL Server 8.0+ (for database phases)
- Power BI Desktop (for dashboard phases)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AkulaSivaSaiBalaji/MediaPulse.git
   cd MediaPulse
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL credentials and preferences
   ```

5. **Run the smoke test suite:**
   ```bash
   pytest tests/test_smoke.py -v
   ```

---

## 6. Project Roadmap

- [x] **Phase 1:** Environment and Project Initialization
- [x] **Phase 2:** YouTube Dataset Inspection and Profiling
- [x] **Phase 3:** Validated Data Cleaning Pipeline and Tests
- [x] **Phase 4:** Exploratory Data Analysis (Matplotlib & Seaborn)
- [x] **Phase 5:** MySQL Relational Schema & Idempotent Ingestion
- [x] **Phase 6:** Advanced SQL Business Analytics & KPI Validation
- [x] **Phase 7:** Power BI Dashboard, Semantic Modeling & DAX Measures
- [ ] **Phase 8:** End-to-End Testing & Pipeline Validation
- [ ] **Phase 9:** Executive Business Insights & Recommendations Report
- [ ] **Phase 10:** GitHub Portfolio Documentation & Interview Preparation Guide

> [!NOTE]
> **Power BI Validation Status Notice:**  
> Power BI project files (`powerbi/MediaPulse_Analytics.pbip`), semantic model schemas (`model.bim`), 27 production DAX measures (`powerbi/dax/measures.dax`), and Power Query M queries have been validated programmatically and reconciled against MySQL 8.0 and pytest (83/83 passing tests). However, **Power BI Desktop GUI visual rendering, interactive slicer cross-filtering, and actual DAX engine execution in the desktop application have not yet been verified** due to headless CI/CD execution constraints, and are documented for manual verification upon opening in Power BI Desktop.

---

## 7. Author & Maintainer

**Akula Siva Sai Balaji**  
- GitHub: [@AkulaSivaSaiBalaji](https://github.com/AkulaSivaSaiBalaji)  
- Target Role: Wipro Analyst L1 (Business Analyst / Data Analyst - Media)
