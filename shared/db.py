import os
import sqlite3
from pathlib import Path

def connect(db_path: str) -> sqlite3.Connection:
    Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def migrate(con: sqlite3.Connection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS queue_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,          -- 'link' | 'manual'
        source_url TEXT,                    -- youtube url if link
        title TEXT,
        description TEXT,
        thumb_mode TEXT,                    -- 'yt' | 'custom'
        created_at TEXT NOT NULL,
        status TEXT NOT NULL                -- 'queued'|'published'|'failed'
    );
    """)
    con.commit()

def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    con.commit()

def get_setting(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None
def init_defaults(con, default_time_ir: str, default_privacy: str) -> None:
    if get_setting(con, "publish_time_ir") is None:
        set_setting(con, "publish_time_ir", default_time_ir)
    if get_setting(con, "privacy") is None:
        set_setting(con, "privacy", default_privacy)

def get_publish_time_ir(con) -> str:
    return get_setting(con, "publish_time_ir") or "17:00"

def set_publish_time_ir(con, hhmm: str) -> None:
    set_setting(con, "publish_time_ir", hhmm)
