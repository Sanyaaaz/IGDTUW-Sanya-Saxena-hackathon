import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{ROOT / 'finrisk.sqlite3'}"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
