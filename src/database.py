import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class HistoryDB:
    def __init__(self, db_path: str = "data/history.db"):
        db_path = db_path.replace("sqlite:///", "").replace("sqlite://", "")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    city TEXT DEFAULT 'Москва',
                    searched_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    screenshot_path TEXT,
                    green_zones_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_searches_address ON searches(address);
            """)

    def save_search(
        self,
        address: str,
        city: str,
        status: str,
        screenshot_path: Optional[str] = None,
        green_zones_json: Optional[str] = None,
    ) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO searches (address, city, searched_at, status, screenshot_path, green_zones_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    address,
                    city,
                    datetime.now().isoformat(),
                    status,
                    screenshot_path,
                    green_zones_json,
                ),
            )
            return cur.lastrowid

    def get_history(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id, address, city, searched_at, status, 
                          screenshot_path, green_zones_json
                   FROM searches
                   ORDER BY searched_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d["green_zones_json"]:
                    d["green_zones"] = json.loads(d["green_zones_json"])
                else:
                    d["green_zones"] = []
                del d["green_zones_json"]
                result.append(d)
            return result

    def get_search(self, search_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM searches WHERE id = ?", (search_id,)
            ).fetchone()
            if row:
                d = dict(row)
                if d["green_zones_json"]:
                    d["green_zones"] = json.loads(d["green_zones_json"])
                else:
                    d["green_zones"] = []
                del d["green_zones_json"]
                return d
            return None
