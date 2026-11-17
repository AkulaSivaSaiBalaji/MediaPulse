"""Smoke tests for MediaPulse environment and configuration."""

import sys
from pathlib import Path
import pytest
from src import config


def test_python_version():
    """Verify that Python 3.11 or higher is running."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"


def test_project_paths_exist():
    """Verify that essential project directories are configured and exist."""
    assert config.BASE_DIR.exists(), "BASE_DIR does not exist"
    assert config.DATA_DIR.exists(), "DATA_DIR does not exist"
    assert config.DATA_RAW_DIR.exists(), "DATA_RAW_DIR does not exist"
    assert config.DATA_PROCESSED_DIR.exists(), "DATA_PROCESSED_DIR does not exist"


def test_core_dependencies_importable():
    """Verify that core data processing, visualization, and DB dependencies can be imported."""
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    import sqlalchemy
    import pymysql

    assert pd.__name__ == "pandas"
    assert np.__name__ == "numpy"
    assert plt is not None
    assert sns.__name__ == "seaborn"
    assert sqlalchemy.__name__ == "sqlalchemy"
    assert pymysql.__name__ == "pymysql"



def test_db_connection_url_generation():
    """Verify safe MySQL connection URL generation and password masking."""
    masked_url = config.get_db_connection_url(mask_password=True)
    assert "********" in masked_url
    assert "mysql+pymysql://" in masked_url
    assert config.DB_NAME in masked_url
