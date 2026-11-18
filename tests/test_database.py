"""Unit tests for MediaPulse Database connection and management module."""

from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src import config, database


def test_db_connection_url_generation():
    """Verify standard and masked database connection URL generators."""
    url = config.get_db_connection_url(mask_password=False)
    assert url.startswith("mysql+pymysql://")
    assert f":{config.DB_PORT}/" in url
    assert config.DB_NAME in url

    masked = config.get_db_connection_url(mask_password=True)
    assert "********" in masked


def test_sqlite_engine_creation(tmp_path):
    """Verify get_engine creates functional engine for SQLite databases."""
    sqlite_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = database.get_engine(db_url=sqlite_url)
    assert isinstance(engine, Engine)

    conn_status = database.test_connection(engine)
    assert conn_status["connected"] is True
    assert conn_status["version"] is not None


def test_test_connection_failure():
    """Verify test_connection returns detailed failure dictionary when host is unreachable."""
    invalid_url = "mysql+pymysql://invalid_user:invalid_pass@127.0.0.1:9999/invalid_db?connect_timeout=1"
    invalid_engine = create_engine(invalid_url)
    status = database.test_connection(invalid_engine)

    assert status["connected"] is False
    assert status["version"] is None
    assert status["error"] is not None


def test_get_db_session_commit_and_rollback(tmp_path):
    """Verify get_db_session transactional context commits and rolls back on failure."""
    sqlite_url = f"sqlite:///{tmp_path / 'session_test.db'}"
    engine = database.get_engine(db_url=sqlite_url)

    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50));"))
        conn.commit()

    # Successful commit
    with database.get_db_session(engine) as session:
        session.execute(text("INSERT INTO test_table (id, name) VALUES (1, 'Alpha');"))

    with engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM test_table WHERE id = 1;")).fetchone()
        assert row[0] == "Alpha"

    # Rollback on exception
    with pytest.raises(ValueError):
        with database.get_db_session(engine) as session:
            session.execute(text("INSERT INTO test_table (id, name) VALUES (2, 'Beta');"))
            raise ValueError("Simulated pipeline error")

    with engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM test_table WHERE id = 2;")).fetchone()
        assert row is None


def test_execute_sql_file_missing_path():
    """Verify execute_sql_file raises FileNotFoundError for non-existent files."""
    missing_path = Path("sql/non_existent_schema.sql")
    with pytest.raises(FileNotFoundError):
        database.execute_sql_file(missing_path)
