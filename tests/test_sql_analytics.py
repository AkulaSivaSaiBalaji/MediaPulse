"""Automated test suite for MediaPulse Phase 6 Advanced SQL Analytics.

Verifies SQL syntax, execution against MySQL, column contracts, deterministic rankings,
null safety, and mathematical reconciliation against Phase 4 Pandas KPIs.
"""

from pathlib import Path
import pytest
import pandas as pd
from sqlalchemy import text

from src import config, database

# Check live MySQL connectivity
is_live_mysql = database.test_connection()["connected"]


def split_sql_queries(file_path: Path) -> list[str]:
    """Parse a multi-query SQL file into individual executable statements."""
    content = file_path.read_text(encoding="utf-8")
    # Remove single-line comments
    clean_lines = [line for line in content.splitlines() if not line.strip().startswith("--")]
    clean_sql = "\n".join(clean_lines)

    # Split by semicolon
    statements = [stmt.strip() for stmt in clean_sql.split(";") if stmt.strip()]
    # Filter out USE statements
    queries = [s for s in statements if not s.upper().startswith("USE ")]
    return queries


@pytest.fixture
def db_engine():
    """Provides active SQLAlchemy database engine."""
    return database.get_engine()


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_advanced_analytics_queries_execution(db_engine):
    """Verify all queries in sql/advanced_analytics.sql execute and return non-empty datasets."""
    sql_path = config.BASE_DIR / "sql" / "advanced_analytics.sql"
    assert sql_path.exists(), "sql/advanced_analytics.sql missing"

    queries = split_sql_queries(sql_path)
    assert len(queries) == 8, f"Expected 8 queries in advanced_analytics.sql, found {len(queries)}"

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        for idx, q in enumerate(queries, 1):
            cur.execute(q)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            assert len(rows) > 0, f"Query {idx} in advanced_analytics.sql returned 0 rows"
            assert len(cols) > 0, f"Query {idx} has no columns"


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_window_functions_queries_execution(db_engine):
    """Verify all queries in sql/window_functions.sql execute and return non-empty datasets."""
    sql_path = config.BASE_DIR / "sql" / "window_functions.sql"
    assert sql_path.exists(), "sql/window_functions.sql missing"

    queries = split_sql_queries(sql_path)
    assert len(queries) == 6, f"Expected 6 queries in window_functions.sql, found {len(queries)}"

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        for idx, q in enumerate(queries, 9):
            cur.execute(q)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            assert len(rows) > 0, f"Query {idx} in window_functions.sql returned 0 rows"
            assert len(cols) > 0, f"Query {idx} has no columns"


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_business_queries_execution(db_engine):
    """Verify all queries in sql/business_queries.sql execute and return non-empty datasets."""
    sql_path = config.BASE_DIR / "sql" / "business_queries.sql"
    assert sql_path.exists(), "sql/business_queries.sql missing"

    queries = split_sql_queries(sql_path)
    assert len(queries) == 6, f"Expected 6 queries in business_queries.sql, found {len(queries)}"

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        for idx, q in enumerate(queries, 15):
            cur.execute(q)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            assert len(rows) > 0, f"Query {idx} in business_queries.sql returned 0 rows"
            assert len(cols) > 0, f"Query {idx} has no columns"


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_category_share_reconciliation(db_engine):
    """Verify Query 1 reconciles exactly to 17 categories and 16,305 unique videos."""
    sql_path = config.BASE_DIR / "sql" / "advanced_analytics.sql"
    q1 = split_sql_queries(sql_path)[0]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q1)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        assert len(df) == 17
        assert df["unique_videos"].sum() == 16305
        assert round(df["catalog_share_pct"].sum(), 1) == 100.0
        assert df.iloc[0]["category_title"] == "Entertainment"
        assert df.iloc[0]["unique_videos"] == 7557


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_top_3_videos_window_ranking(db_engine):
    """Verify Query 9 limits to <= 3 videos per category without exceeding partition bounds."""
    sql_path = config.BASE_DIR / "sql" / "window_functions.sql"
    q9 = split_sql_queries(sql_path)[0]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q9)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        assert "rank_in_category" in df.columns
        assert df["rank_in_category"].max() <= 3
        # Max count per category is 3
        cat_counts = df["category_title"].value_counts()
        assert (cat_counts <= 3).all()
        # Entertainment has 3
        assert cat_counts["Entertainment"] == 3


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_month_over_month_lag_calculation(db_engine):
    """Verify Query 11 calculates valid LAG metrics with null in initial month."""
    sql_path = config.BASE_DIR / "sql" / "window_functions.sql"
    q11 = split_sql_queries(sql_path)[2]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q11)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        assert len(df) == 8  # 8 months: 2017-11 to 2018-06
        # First row prior_month_snapshots is None
        assert pd.isna(df.iloc[0]["prior_month_snapshots"])
        # Second row onward has non-null prior month
        assert not pd.isna(df.iloc[1]["prior_month_snapshots"])
        # Snapshot net change = total - prior
        assert df.iloc[1]["snapshot_net_change"] == df.iloc[1]["total_snapshots"] - df.iloc[1]["prior_month_snapshots"]


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_rolling_7day_moving_averages(db_engine):
    """Verify Query 12 window framing calculates accurate 7-day trailing aggregates."""
    sql_path = config.BASE_DIR / "sql" / "window_functions.sql"
    q12 = split_sql_queries(sql_path)[3]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q12)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        assert len(df) == 205  # 205 distinct trending dates
        # On row 7 (index 6), rolling_7day_total equals sum of first 7 rows
        first_7_sum = int(df.iloc[:7]["daily_snapshots"].sum())
        assert int(df.iloc[6]["rolling_7day_total_snapshots"]) == first_7_sum


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_category_median_engagement_reconciliation(db_engine):
    """Verify Query 16 median engagement rate matches Phase 4 EDA benchmarks."""
    sql_path = config.BASE_DIR / "sql" / "business_queries.sql"
    q16 = split_sql_queries(sql_path)[1]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q16)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        # Set category_title as index for direct lookup
        cat_map = df.set_index("category_title")["median_engagement_rate"].to_dict()

        # Reconcile key findings from Phase 4
        assert pytest.approx(float(cat_map["Science & Technology"]), abs=0.01) == 7.5610
        assert pytest.approx(float(cat_map["Education"]), abs=0.01) == 5.6205
        assert pytest.approx(float(cat_map["Comedy"]), abs=0.01) == 4.2236
        assert pytest.approx(float(cat_map["Entertainment"]), abs=0.01) == 0.5823
        assert pytest.approx(float(cat_map["News & Politics"]), abs=0.01) == 0.6609


@pytest.mark.skipif(not is_live_mysql, reason="Requires live MySQL server")
def test_top_channels_portfolio_reconciliation(db_engine):
    """Verify Query 15 extracts top channel 'Study IQ education' with 169 unique videos."""
    sql_path = config.BASE_DIR / "sql" / "business_queries.sql"
    q15 = split_sql_queries(sql_path)[0]

    with db_engine.connect() as conn:
        cur = conn.connection.cursor()
        cur.execute(q15)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        assert len(df) == 10
        top_row = df.iloc[0]
        assert top_row["channel_title"] == "Study IQ education"
        assert top_row["unique_videos"] == 169
        assert top_row["max_single_video_views"] == 454576
