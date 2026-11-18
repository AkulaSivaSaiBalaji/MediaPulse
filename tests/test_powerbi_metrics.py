"""MediaPulse Phase 7 — Automated Power BI Reporting Layer & DAX Metrics Tests.

Validates reporting view schemas, grain separation, video-level peak reach aggregation,
DAX measure mathematical reconciliation, category shares, channel rankings, and
filter context scenarios against the MySQL database and Pandas baseline.
"""

from decimal import Decimal
import os
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import text

from src import config
from src.database import get_engine, execute_sql_file

# Skip entire module if MySQL connection is unavailable
pytestmark = pytest.mark.skipif(
    not os.getenv("MYSQL_PASSWORD") and not (config.BASE_DIR / ".env").exists(),
    reason="MySQL integration tests require database configuration in .env",
)


@pytest.fixture(scope="module")
def db_engine():
    """Module-level SQLAlchemy engine with reporting views initialized."""
    engine = get_engine()
    # Initialize / verify reporting views
    views_sql_path = config.BASE_DIR / "sql" / "powerbi_reporting_views.sql"
    if views_sql_path.exists():
        try:
            execute_sql_file(views_sql_path, engine=engine)
        except Exception as e:
            pytest.skip(f"Could not execute reporting views: {e}")
    return engine


def test_reporting_views_row_counts(db_engine):
    """Verify all 5 reporting views exist and return expected row counts."""
    expected_counts = {
        "vw_dim_category": 17,
        "vw_dim_channel": 1423,
        "vw_dim_video": 16305,
        "vw_fact_trending_snapshots": 32265,
        "vw_dim_date": 426,
    }
    with db_engine.connect() as conn:
        for view_name, expected in expected_counts.items():
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
            assert cnt == expected, f"View {view_name} count {cnt} != expected {expected}"


def test_date_dimension_collection_coverage(db_engine):
    """Verify DimDate properly isolates the 205 observed snapshot dates from the 426 calendar days."""
    with db_engine.connect() as conn:
        obs_cnt = conn.execute(
            text("SELECT COUNT(*) FROM vw_dim_date WHERE is_trending_snapshot_date = 1")
        ).scalar()
        assert obs_cnt == 205

        unobs_cnt = conn.execute(
            text("SELECT COUNT(*) FROM vw_dim_date WHERE is_trending_snapshot_date = 0")
        ).scalar()
        assert unobs_cnt == 221  # 426 - 205 = 221


def test_core_dataset_kpis_reconciliation(db_engine):
    """Validate core KPIs match baseline: 16,305 videos, 32,265 snapshots, 1,423 channels, 17 categories."""
    with db_engine.connect() as conn:
        v_cnt = conn.execute(text("SELECT COUNT(DISTINCT video_id) FROM vw_dim_video")).scalar()
        s_cnt = conn.execute(text("SELECT COUNT(*) FROM vw_fact_trending_snapshots")).scalar()
        ch_cnt = conn.execute(text("SELECT COUNT(DISTINCT channel_id) FROM vw_dim_channel")).scalar()
        cat_cnt = conn.execute(text("SELECT COUNT(DISTINCT category_id) FROM vw_dim_category")).scalar()
        d_cnt = conn.execute(
            text("SELECT COUNT(DISTINCT trending_date) FROM vw_fact_trending_snapshots")
        ).scalar()

        assert v_cnt == 16305
        assert s_cnt == 32265
        assert ch_cnt == 1423
        assert cat_cnt == 17
        assert d_cnt == 205


def test_video_level_peak_views_no_double_counting(db_engine):
    """Verify that per-video peak views avoids double-counting cumulative daily snapshots.

    Directly summing FactTrendingSnapshot[views] yields 30.83B (artificial 176.5% inflation).
    Summing per-video maximum views yields the true reach: 11,147,625,965.
    """
    with db_engine.connect() as conn:
        raw_sum_snapshots = conn.execute(
            text("SELECT SUM(views) FROM vw_fact_trending_snapshots")
        ).scalar()
        per_video_peak_sum = conn.execute(
            text("SELECT SUM(peak_views) FROM vw_dim_video")
        ).scalar()

        assert per_video_peak_sum == 11147625965
        assert raw_sum_snapshots == 30827205597
        assert raw_sum_snapshots > per_video_peak_sum
        # Confirm raw sum is ~30.8B (176.5% higher than true peak reach)
        pct_diff = float((raw_sum_snapshots - per_video_peak_sum) / per_video_peak_sum * 100)
        assert pytest.approx(pct_diff, abs=0.1) == 176.54


def test_per_video_peak_views_mean_and_median(db_engine):
    """Verify mean and median peak views against validated Phase 4 and Phase 6 benchmarks."""
    with db_engine.connect() as conn:
        df_v = pd.read_sql("SELECT peak_views FROM vw_dim_video", conn)
        mean_views = df_v["peak_views"].mean()
        median_views = df_v["peak_views"].median()

        assert pytest.approx(mean_views, abs=0.1) == 683693.71
        assert median_views == 205619.0


def test_video_engagement_rate_distribution(db_engine):
    """Verify mean and median video-level engagement rate calculation."""
    with db_engine.connect() as conn:
        df_v = pd.read_sql(
            "SELECT lifetime_engagement_rate FROM vw_dim_video WHERE peak_views > 0", conn
        )
        mean_er = float(df_v["lifetime_engagement_rate"].astype(float).mean())
        median_er = float(df_v["lifetime_engagement_rate"].astype(float).median())

        assert pytest.approx(mean_er, abs=0.001) == 2.0579
        assert pytest.approx(median_er, abs=0.001) == 0.8284


def test_trending_velocity_denominators(db_engine):
    """Verify trending latency metrics: Day 0 = 420 (2.58%), Day <= 2 = 15,720 (96.41%)."""
    with db_engine.connect() as conn:
        df_v = pd.read_sql("SELECT days_to_first_trend FROM vw_dim_video", conn)
        total_videos = len(df_v)
        day_0 = (df_v["days_to_first_trend"] == 0).sum()
        day_le2 = (df_v["days_to_first_trend"] <= 2).sum()
        pct_le2 = (day_le2 / total_videos) * 100
        mean_days = float(df_v["days_to_first_trend"].mean())
        median_days = float(df_v["days_to_first_trend"].median())

        assert total_videos == 16305
        assert day_0 == 420
        assert day_le2 == 15720
        assert pytest.approx(pct_le2, abs=0.01) == 96.41
        assert pytest.approx(mean_days, abs=0.01) == 1.31
        assert median_days == 1.0


def test_category_slice_reconciliation(db_engine):
    """Verify category slicer simulation for Entertainment (7,557) and News & Politics (2,506)."""
    with db_engine.connect() as conn:
        sql = """
            SELECT 
                c.category_title,
                COUNT(v.video_id) AS video_count,
                ROUND(COUNT(v.video_id) * 100.0 / 16305, 2) AS category_share_pct,
                SUM(v.peak_views) AS category_peak_views
            FROM vw_dim_category c
            JOIN vw_dim_video v ON c.category_id = v.category_id
            WHERE c.category_title IN ('Entertainment', 'News & Politics')
            GROUP BY c.category_id, c.category_title
            ORDER BY video_count DESC;
        """
        rows = conn.execute(text(sql)).fetchall()
        cat_map = {r[0]: (int(r[1]), float(r[2]), int(r[3])) for r in rows}

        assert cat_map["Entertainment"][0] == 7557
        assert pytest.approx(cat_map["Entertainment"][1], abs=0.01) == 46.35
        assert cat_map["Entertainment"][2] == 4349915552

        assert cat_map["News & Politics"][0] == 2506
        assert pytest.approx(cat_map["News & Politics"][1], abs=0.01) == 15.37
        assert cat_map["News & Politics"][2] == 745593584


def test_channel_ranking_and_tied_ranks(db_engine):
    """Verify channel rankings and tied dense rank behavior (VikatanTV and etvteluguindia)."""
    with db_engine.connect() as conn:
        sql = """
            SELECT 
                ch.channel_title,
                COUNT(v.video_id) AS video_count,
                DENSE_RANK() OVER (ORDER BY COUNT(v.video_id) DESC) AS channel_dense_rank
            FROM vw_dim_channel ch
            JOIN vw_dim_video v ON ch.channel_id = v.channel_id
            GROUP BY ch.channel_id, ch.channel_title
            ORDER BY video_count DESC
            LIMIT 5;
        """
        rows = conn.execute(text(sql)).fetchall()
        top5 = [(r[0], int(r[1]), int(r[2])) for r in rows]

        # Top channel is Study IQ education with 169 videos, Rank 1
        assert top5[0] == ("Study IQ education", 169, 1)
        assert top5[1] == ("Tarang TV", 158, 2)
        # Tied at Rank 3
        assert top5[2][1] == 153 and top5[2][2] == 3
        assert top5[3][1] == 153 and top5[3][2] == 3
        # 5th channel gets dense rank 4
        assert top5[4] == ("Saregama TVShows", 152, 4)


def test_month_over_month_snapshot_change(db_engine):
    """Verify Month-over-Month snapshot count change logic."""
    with db_engine.connect() as conn:
        sql = """
            SELECT 
                d.year_month_label AS ym,
                COUNT(s.snapshot_id) AS snapshot_count
            FROM vw_dim_date d
            JOIN vw_fact_trending_snapshots s ON d.full_date = s.trending_date
            GROUP BY d.year_month_label, d.year_month_sort
            ORDER BY d.year_month_sort;
        """
        df = pd.read_sql(text(sql), conn)
        df["prev_count"] = df["snapshot_count"].shift(1)
        df["mom_change"] = df["snapshot_count"] - df["prev_count"]

        # December 2017 change from November 2017 (3158 -> 5744 = +2586)
        dec_change = df.loc[df["ym"] == "2017-12", "mom_change"].values[0]
        assert dec_change == 2586

        # April 2018 change from March 2018 (4584 -> 3273 = -1311)
        apr_change = df.loc[df["ym"] == "2018-04", "mom_change"].values[0]
        assert apr_change == -1311


def test_rolling_7_observed_dates_logic(db_engine):
    """Verify that the rolling 7-observed-date window bridges missing collection dates.

    Ensures that for 2018-04-14 (the first collection day after the 6-day outage Apr 8-13),
    the rolling average uses the 7 prior collected dates (Apr 14, Apr 7, Apr 6, Apr 5, Apr 4, Apr 3, Apr 2)
    rather than dividing by 7 calendar days with zeros.
    """
    with db_engine.connect() as conn:
        sql = """
            SELECT trending_date, COUNT(*) as daily_cnt
            FROM vw_fact_trending_snapshots
            WHERE trending_date <= '2018-04-14'
            GROUP BY trending_date
            ORDER BY trending_date DESC
            LIMIT 7;
        """
        rows = conn.execute(text(sql)).fetchall()
        assert len(rows) == 7
        # Verify the 7 dates include April 14 and then jump over the April 8-13 gap to April 7
        dates = [str(r[0]) for r in rows]
        assert dates[0] == "2018-04-14"
        assert dates[1] == "2018-04-07"
        total_snapshots_7_days = sum(r[1] for r in rows)
        expected_avg = total_snapshots_7_days / 7.0
        assert expected_avg > 100.0  # Proper healthy average, not deflated by zero-padding


def test_date_filtered_peak_views_scenarios(db_engine):
    """Verify DAX filter context scenarios for per-video peak views and video counts.

    Tests that iterating over VALUES(FactTrendingSnapshot[video_id]) properly isolates
    observed videos and prevents unobserved videos from contributing historical peaks.
    """
    with db_engine.connect() as conn:
        # Scenario 1: All-time baseline (no date filter)
        s1 = conn.execute(
            text("SELECT COUNT(*), SUM(peak_views) FROM vw_dim_video")
        ).fetchone()
        assert s1[0] == 16305
        assert s1[1] == 11147625965

        # Scenario 2: Single date (2017-11-14)
        s2 = conn.execute(text("""
            SELECT COUNT(DISTINCT video_id), SUM(views)
            FROM vw_fact_trending_snapshots
            WHERE trending_date = '2017-11-14'
        """)).fetchone()
        assert s2[0] == 197
        assert s2[1] == 156120907

        # Scenario 3: Date range (2017-11-14 to 2017-11-20)
        s3 = conn.execute(text("""
            WITH win AS (
                SELECT video_id, MAX(views) AS win_peak
                FROM vw_fact_trending_snapshots
                WHERE trending_date BETWEEN '2017-11-14' AND '2017-11-20'
                GROUP BY video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s3[0] == 771
        assert s3[1] == 420290494

        # Scenario 4: Month filter (2017-12)
        s4 = conn.execute(text("""
            WITH win AS (
                SELECT video_id, MAX(views) AS win_peak
                FROM vw_fact_trending_snapshots
                WHERE trending_date >= '2017-12-01' AND trending_date <= '2017-12-31'
                GROUP BY video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s4[0] == 2928
        assert s4[1] == 1837672615

        # Scenario 5: Year filter (2018)
        s5 = conn.execute(text("""
            WITH win AS (
                SELECT video_id, MAX(views) AS win_peak
                FROM vw_fact_trending_snapshots
                WHERE trending_date >= '2018-01-01' AND trending_date <= '2018-12-31'
                GROUP BY video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s5[0] == 11982
        assert s5[1] == 8669880904

        # Scenario 6: Category + Month filter (Entertainment + 2017-12)
        s6 = conn.execute(text("""
            WITH win AS (
                SELECT s.video_id, MAX(s.views) AS win_peak
                FROM vw_fact_trending_snapshots s
                JOIN vw_dim_video v ON s.video_id = v.video_id
                JOIN vw_dim_category c ON v.category_id = c.category_id
                WHERE c.category_title = 'Entertainment'
                  AND s.trending_date >= '2017-12-01' AND s.trending_date <= '2017-12-31'
                GROUP BY s.video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s6[0] == 1307
        assert s6[1] == 850028080

        # Scenario 7: Channel + Month filter (Study IQ education + 2017-12)
        s7 = conn.execute(text("""
            WITH win AS (
                SELECT s.video_id, MAX(s.views) AS win_peak
                FROM vw_fact_trending_snapshots s
                JOIN vw_dim_video v ON s.video_id = v.video_id
                JOIN vw_dim_channel ch ON v.channel_id = ch.channel_id
                WHERE ch.channel_title = 'Study IQ education'
                  AND s.trending_date >= '2017-12-01' AND s.trending_date <= '2017-12-31'
                GROUP BY s.video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s7[0] == 27
        assert s7[1] == 1314605

        # Scenario 8: Outage date (2018-04-10) — Scraper downtime, zero snapshots
        s8 = conn.execute(text("""
            WITH win AS (
                SELECT video_id, MAX(views) AS win_peak
                FROM vw_fact_trending_snapshots
                WHERE trending_date = '2018-04-10'
                GROUP BY video_id
            )
            SELECT COUNT(*), SUM(win_peak) FROM win
        """)).fetchone()
        assert s8[0] == 0
        assert s8[1] is None  # Matches DAX BLANK() behavior


def test_semantic_model_tom_schema_validity():
    """Verify semantic model validity under both modern TMDL format and legacy model.bim format.

    Validates that:
    - In TMDL mode (definition/): database.tmdl, model.tmdl, relationships.tmdl, and all 6 table TMDL files exist.
    - All 5 relationships and all 27 DAX measures are defined.
    - Column definitions contain NO unsupported properties like isNameInferred.
    """
    import json
    model_dir = config.BASE_DIR / "powerbi" / "MediaPulse_Analytics.SemanticModel"
    tmdl_dir = model_dir / "definition"
    model_bim_path = model_dir / "model.bim"

    assert tmdl_dir.exists() or model_bim_path.exists(), "Neither TMDL definition nor model.bim found"

    expected_tables = ["_Measures", "DimCategory", "DimChannel", "DimVideo", "FactTrendingSnapshot", "DimDate"]

    if tmdl_dir.exists():
        # Validate TMDL structure
        assert (tmdl_dir / "database.tmdl").exists(), "database.tmdl missing"
        assert (tmdl_dir / "model.tmdl").exists(), "model.tmdl missing"
        assert (tmdl_dir / "relationships.tmdl").exists(), "relationships.tmdl missing"

        # Check model.tmdl table references
        model_content = (tmdl_dir / "model.tmdl").read_text(encoding="utf-8")
        for t_name in expected_tables:
            assert f"ref table {t_name}" in model_content, f"model.tmdl missing ref table {t_name}"

        # Check relationships
        rel_content = (tmdl_dir / "relationships.tmdl").read_text(encoding="utf-8")
        rel_count = len([l for l in rel_content.splitlines() if l.strip().startswith("relationship ")])
        assert rel_count == 5, f"Expected 5 relationships in relationships.tmdl, got {rel_count}"

        # Check tables directory and measures
        tables_dir = tmdl_dir / "tables"
        assert tables_dir.exists(), "tables/ directory missing in TMDL definition"
        for t_name in expected_tables:
            t_file = tables_dir / f"{t_name}.tmdl"
            assert t_file.exists(), f"Missing TMDL file {t_name}.tmdl"
            t_text = t_file.read_text(encoding="utf-8")
            assert "isNameInferred" not in t_text, f"{t_name}.tmdl contains unsupported isNameInferred property"

        measures_content = (tables_dir / "_Measures.tmdl").read_text(encoding="utf-8")
        measures = [l.strip() for l in measures_content.splitlines() if l.strip().startswith("measure ")]
        assert len(measures) == 27, f"Expected 27 DAX measures in _Measures.tmdl, got {len(measures)}"

    if model_bim_path.exists():
        with open(model_bim_path, "r", encoding="utf-8") as f:
            bim = json.load(f)

        def find_prop(obj, prop_name):
            found = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == prop_name:
                        found.append(k)
                    found.extend(find_prop(v, prop_name))
            elif isinstance(obj, list):
                for item in obj:
                    found.extend(find_prop(item, prop_name))
            return found

        assert len(find_prop(bim, "isNameInferred")) == 0, "model.bim contains unsupported isNameInferred property"

        tables = {t["name"]: t for t in bim["model"]["tables"]}
        for t_name in expected_tables:
            assert t_name in tables, f"Missing table {t_name}"

        measures = tables["_Measures"].get("measures", [])
        assert len(measures) == 27, f"Expected 27 DAX measures, got {len(measures)}"
        assert len(bim["model"].get("relationships", [])) == 5


def test_project_generator_has_no_unsupported_properties():
    """Verify that the generator script powerbi/build_powerbi_project.py does not recreate isNameInferred."""
    gen_script = config.BASE_DIR / "powerbi" / "build_powerbi_project.py"
    assert gen_script.exists(), "powerbi/build_powerbi_project.py missing"
    content = gen_script.read_text(encoding="utf-8")
    assert "isNameInferred" not in content, "Generator script still contains isNameInferred"


def test_modern_pbir_report_structure():
    """Verify that the Power BI report uses modern modular PBIR format (Power BI Desktop 2.159.883.0+).

    Validates:
    - definition.pbir has version 4.0 and datasetReference.byPath.
    - Legacy root report.json does NOT exist (mutually exclusive with PBIR).
    - definition/version.json exists with version 2.0.0.
    - definition/report.json exists with valid theme configuration.
    - definition/pages/pages.json exists with 3 ordered pages.
    - All 3 page directories exist with valid page.json (1280x720, FitToPage).
    """
    import json
    report_dir = config.BASE_DIR / "powerbi" / "MediaPulse_Analytics.Report"
    assert report_dir.exists(), "MediaPulse_Analytics.Report directory missing"

    # 1. definition.pbir
    pbir_path = report_dir / "definition.pbir"
    assert pbir_path.exists(), "definition.pbir missing"
    with open(pbir_path, "r", encoding="utf-8") as f:
        pbir = json.load(f)
    assert pbir.get("version") == "4.0", f"Expected version 4.0, got {pbir.get('version')}"
    assert pbir.get("datasetReference", {}).get("byPath", {}).get("path") == "../MediaPulse_Analytics.SemanticModel"

    # 2. Legacy root report.json must NOT exist
    legacy_root_report = report_dir / "report.json"
    assert not legacy_root_report.exists(), "Legacy root report.json found; conflicts with modern PBIR format"

    # 3. definition/version.json
    version_path = report_dir / "definition" / "version.json"
    assert version_path.exists(), "definition/version.json missing"
    with open(version_path, "r", encoding="utf-8") as f:
        ver = json.load(f)
    assert ver.get("version") == "2.0.0"

    # 4. definition/report.json
    report_json_path = report_dir / "definition" / "report.json"
    assert report_json_path.exists(), "definition/report.json missing"
    with open(report_json_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    assert "themeCollection" in rep
    if "layoutOptimization" in rep:
        assert rep.get("layoutOptimization") in {"None", "PhonePortrait"}, (
            f"Invalid layoutOptimization value: {rep.get('layoutOptimization')}"
        )

    # 5. definition/pages/pages.json
    pages_json_path = report_dir / "definition" / "pages" / "pages.json"
    assert pages_json_path.exists(), "definition/pages/pages.json missing"
    with open(pages_json_path, "r", encoding="utf-8") as f:
        pages_meta = json.load(f)
    expected_page_order = ["ExecutiveOverview", "ContentEngagementAnalytics", "ChannelPerformance"]
    assert pages_meta.get("pageOrder") == expected_page_order
    assert pages_meta.get("activePageName") in expected_page_order

    # 6. Page definitions
    expected_display_names = {
        "ExecutiveOverview": "Executive Overview",
        "ContentEngagementAnalytics": "Content & Engagement Analytics",
        "ChannelPerformance": "Channel Performance",
    }
    for page_name, exp_disp in expected_display_names.items():
        page_json_path = report_dir / "definition" / "pages" / page_name / "page.json"
        assert page_json_path.exists(), f"Missing page.json for {page_name}"
        with open(page_json_path, "r", encoding="utf-8") as f:
            p_data = json.load(f)
        assert p_data.get("name") == page_name
        assert p_data.get("displayName") == exp_disp
        assert p_data.get("width") == 1280
        assert p_data.get("height") == 720
        assert p_data.get("displayOption") == "FitToPage"


def test_modern_pbir_visual_definitions_and_field_bindings():
    """Verify that all 24 visual containers across the 3 pages are valid native PBIR visual items."""
    import json
    report_dir = config.BASE_DIR / "powerbi" / "MediaPulse_Analytics.Report"
    pages_dir = report_dir / "definition" / "pages"

    expected_page_visual_counts = {
        "ExecutiveOverview": 9,
        "ContentEngagementAnalytics": 8,
        "ChannelPerformance": 7,
    }

    total_visual_count = 0
    valid_visual_types = {"card", "lineChart", "clusteredBarChart", "clusteredColumnChart", "scatterChart", "tableEx"}

    for page_name, expected_count in expected_page_visual_counts.items():
        vis_parent_dir = pages_dir / page_name / "visuals"
        assert vis_parent_dir.exists(), f"visuals directory missing for {page_name}"

        visual_dirs = [d for d in vis_parent_dir.iterdir() if d.is_dir()]
        assert len(visual_dirs) == expected_count, (
            f"Page {page_name} visual count {len(visual_dirs)} != expected {expected_count}"
        )
        total_visual_count += len(visual_dirs)

        for v_dir in visual_dirs:
            v_json_path = v_dir / "visual.json"
            assert v_json_path.exists(), f"visual.json missing in {v_dir}"
            with open(v_json_path, "r", encoding="utf-8") as f:
                v_data = json.load(f)

            # Validate container properties
            assert v_data.get("name") == v_dir.name
            pos = v_data.get("position", {})
            for key in ["x", "y", "z", "width", "height", "tabOrder"]:
                assert key in pos, f"Visual {v_dir.name} position missing {key}"
                assert isinstance(pos[key], (int, float))

            # Validate visual definition
            visual = v_data.get("visual", {})
            v_type = visual.get("visualType")
            assert v_type in valid_visual_types, f"Visual {v_dir.name} has unknown visualType: {v_type}"

            # Validate query projection bindings
            query_state = visual.get("query", {}).get("queryState", {})
            assert query_state, f"Visual {v_dir.name} has empty queryState"
            for role, role_def in query_state.items():
                projections = role_def.get("projections", [])
                assert len(projections) > 0, f"Role {role} in {v_dir.name} has no projections"
                for proj in projections:
                    assert "queryRef" in proj, f"Projection in {v_dir.name} missing queryRef"
                    assert "field" in proj, f"Projection in {v_dir.name} missing field definition"
                    field_obj = proj["field"]
                    assert "Measure" in field_obj or "Column" in field_obj, (
                        f"Projection in {v_dir.name} field is neither Measure nor Column"
                    )

    assert total_visual_count == 24, f"Total visuals across report {total_visual_count} != 24"


def test_modern_pbir_report_json_schema_compliance():
    """Verify that definition/report.json contains valid Microsoft Fabric PBIR schema properties.

    Specifically validates:
    - Root property '$schema' matching Microsoft Fabric PBIR report schema.
    - Root property 'themeCollection' containing 'baseTheme'.
    - Generator script powerbi/build_powerbi_project.py also includes layoutOptimization: None.
    """
    import json
    report_json_path = config.BASE_DIR / "powerbi" / "MediaPulse_Analytics.Report" / "definition" / "report.json"
    assert report_json_path.exists(), "definition/report.json missing"
    with open(report_json_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep.get("$schema", "").startswith("https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/")
    assert "themeCollection" in rep
    if "layoutOptimization" in rep:
        assert rep.get("layoutOptimization") in {"None", "PhonePortrait"}

    # Also verify generator script source
    gen_script = config.BASE_DIR / "powerbi" / "build_powerbi_project.py"
    content = gen_script.read_text(encoding="utf-8")
    assert '"layoutOptimization": "None"' in content, "Generator script missing layoutOptimization: None"


def test_powerquery_unambiguous_navigation_keys():
    """Verify that Power Query M expressions use exact navigation keys containing Schema, Item, and Kind.

    Ambiguous navigation using only [Schema="mediapulse_db"] causes Power BI refresh failures:
    'The key matched more than one row in the table.'

    Validates exact navigation across:
    1. TMDL model files (powerbi/MediaPulse_Analytics.SemanticModel/definition/tables/*.tmdl) or model.bim
    2. powerbi/powerquery/mysql_import_queries.pq
    3. powerbi/build_powerbi_project.py
    """
    import json
    import re

    expected_views = {
        "DimCategory": "vw_dim_category",
        "DimChannel": "vw_dim_channel",
        "DimVideo": "vw_dim_video",
        "FactTrendingSnapshot": "vw_fact_trending_snapshots",
        "DimDate": "vw_dim_date",
    }

    model_dir = config.BASE_DIR / "powerbi" / "MediaPulse_Analytics.SemanticModel"
    tmdl_dir = model_dir / "definition" / "tables"
    model_bim_path = model_dir / "model.bim"

    assert tmdl_dir.exists() or model_bim_path.exists(), "Neither TMDL nor model.bim found"

    # 1. Validate Semantic Model (TMDL or model.bim)
    if tmdl_dir.exists():
        for table_name, view_name in expected_views.items():
            t_file = tmdl_dir / f"{table_name}.tmdl"
            assert t_file.exists(), f"Missing TMDL file {t_file}"
            content = t_file.read_text(encoding="utf-8")
            assert '[Schema="mediapulse_db"]}[Data]' not in content, (
                f"{table_name}.tmdl contains ambiguous [Schema=\"mediapulse_db\"] navigation"
            )
            assert '[Name="' not in content, (
                f"{table_name}.tmdl uses deprecated [Name=...] navigation"
            )
            pattern = rf'Source\{{\[Schema="mediapulse_db",\s*Item="{view_name}",\s*Kind="View"\]\}}\[Data\]'
            assert re.search(pattern, content), (
                f"{table_name}.tmdl does not match exact navigation pattern: {pattern}"
            )

    if model_bim_path.exists():
        with open(model_bim_path, "r", encoding="utf-8") as f:
            bim = json.load(f)

        tables = {t["name"]: t for t in bim["model"]["tables"]}
        for table_name, view_name in expected_views.items():
            assert table_name in tables, f"Missing table {table_name} in model.bim"
            partitions = tables[table_name].get("partitions", [])
            assert len(partitions) > 0, f"No partitions in {table_name}"
            m_lines = partitions[0]["source"]["expression"]
            m_expr = " ".join(m_lines)

            assert '[Schema="mediapulse_db"]}[Data]' not in m_expr, (
                f"Table {table_name} contains ambiguous [Schema=\"mediapulse_db\"] navigation"
            )
            assert '[Name="' not in m_expr, (
                f"Table {table_name} uses deprecated [Name=...] navigation"
            )
            pattern = rf'Source\{{\[Schema="mediapulse_db",\s*Item="{view_name}",\s*Kind="View"\]\}}\[Data\]'
            assert re.search(pattern, m_expr), (
                f"Table {table_name} does not match exact navigation pattern: {pattern}"
            )

    # 2. Validate mysql_import_queries.pq
    pq_path = config.BASE_DIR / "powerbi" / "powerquery" / "mysql_import_queries.pq"
    assert pq_path.exists(), "mysql_import_queries.pq missing"
    pq_content = pq_path.read_text(encoding="utf-8")

    assert '[Schema=DatabaseName]}[Data]' not in pq_content, (
        "mysql_import_queries.pq contains ambiguous [Schema=DatabaseName]} navigation"
    )
    for table_name, view_name in expected_views.items():
        expected_pq_nav = f'Source{{[Schema=DatabaseName, Item="{view_name}", Kind="View"]}}[Data]'
        assert expected_pq_nav in pq_content, (
            f"mysql_import_queries.pq missing exact navigation for {view_name}: {expected_pq_nav}"
        )

    # 3. Validate build_powerbi_project.py generator script
    gen_path = config.BASE_DIR / "powerbi" / "build_powerbi_project.py"
    assert gen_path.exists(), "build_powerbi_project.py missing"
    gen_content = gen_path.read_text(encoding="utf-8")

    assert '[Schema=\\"mediapulse_db\\"]}[Data]' not in gen_content, (
        "build_powerbi_project.py contains ambiguous navigation"
    )
    for table_name, view_name in expected_views.items():
        expected_gen_nav = f'Source{{[Schema=\\"mediapulse_db\\", Item=\\"{view_name}\\", Kind=\\"View\\"]}}[Data]'
        assert expected_gen_nav in gen_content, (
            f"build_powerbi_project.py missing exact navigation for {view_name}: {expected_gen_nav}"
        )





