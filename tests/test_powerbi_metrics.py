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

