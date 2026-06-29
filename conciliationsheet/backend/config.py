import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"

DATABASE_DIR = BASE_DIR / "backend" / "database"
DATABASE_PATH = DATABASE_DIR / "conciliationsheet.db"

SCHEMA_PATH = DATABASE_DIR / "schema.sql"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
