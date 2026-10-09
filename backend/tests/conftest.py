import os
from pathlib import Path

test_db = Path(__file__).resolve().parents[2] / ".presentation-build" / "pytest.sqlite3"
test_db.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db}")
