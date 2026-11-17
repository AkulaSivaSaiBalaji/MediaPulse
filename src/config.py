"""Configuration module for MediaPulse.

Centralizes paths, environment variables, database settings, and project constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
DATA_RAW_DIR: Path = DATA_DIR / "raw"
DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"
SQL_DIR: Path = BASE_DIR / "sql"
REPORTS_DIR: Path = BASE_DIR / "reports"
NOTEBOOKS_DIR: Path = BASE_DIR / "notebooks"
DASHBOARD_DIR: Path = BASE_DIR / "dashboard"

# Load environment variables from .env if present
ENV_FILE: Path = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()  # Fallback to default search

# Database Configuration
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_NAME: str = os.getenv("DB_NAME", "mediapulse_db")

# Logging & Pipeline Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


def get_db_connection_url(mask_password: bool = False) -> str:
    """Generate SQLAlchemy connection URL for MySQL.

    Args:
        mask_password: If True, replaces password with asterisks for safe logging.

    Returns:
        Formatted MySQL connection URI.
    """
    password = "********" if mask_password else DB_PASSWORD
    return f"mysql+pymysql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
