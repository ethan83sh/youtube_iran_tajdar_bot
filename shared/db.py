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
        status TEXT NOT NULL                -- 'queued'|'picking'|'published'|'failed'
    );
    """)

    def _add_col_safe(table: str, col: str, coldef: str):
        cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")

    # columns for add_link/edit flows
    _add_col_safe("queue_items", "title_mode", "TEXT")            # 'yt'|'manual'
    _add_col_safe("queue_items", "desc_mode", "TEXT")             # 'yt'|'manual'
    _add_col_safe("queue_items", "manual_title", "TEXT")
    _add_col_safe("queue_items", "manual_desc", "TEXT")
    _add_col_safe("queue_items", "manual_thumb_file_id", "TEXT")
    _add_col_safe("queue_items", "sort_order", "INTEGER")
    _add_col_safe("queue_items", "picked_at", "TEXT")
    _add_col_safe("queue_items", "published_at", "TEXT")

    # backfill sort_order for existing rows
    con.execute("""
    UPDATE queue_items
    SET sort_order = id
    WHERE sort_order IS NULL
    """)

    con.commit()


def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
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


def add_queue_item_link(
    con,
    url: str,
    title: str | None = None,
    description: str | None = None,
    thumb_mode: str = "yt",
) -> int:
    cur = con.execute(
        """
        INSERT INTO queue_items(source_type, source_url, title, description, thumb_mode, created_at, status)
        VALUES(?, ?, ?, ?, ?, datetime('now'), 'queued')
        """,
        ("link", url, title, description, thumb_mode),
    )
    con.commit()
    return int(cur.lastrowid)


def list_queued(con, limit: int = 20):
    return con.execute(
        "SELECT id, source_type, source_url, title, created_at, sort_order FROM queue_items "
        "WHERE status='queued' ORDER BY sort_order ASC, id ASC LIMIT ?",
        (limit,),
    ).fetchall()


def delete_queue_item(con, item_id: int) -> None:
    con.execute("DELETE FROM queue_items WHERE id=? AND status IN ('queued','picking')", (item_id,))
    con.commit()


def get_queue_item(con, item_id: int):
    # نکته مهم: بعد از pick_next_for_today، status می‌شود picking
    return con.execute(
        "SELECT * FROM queue_items WHERE id=? AND status IN ('queued','picking')",
        (item_id,),
    ).fetchone()


def update_queue_title(con, item_id: int, title: str):
    con.execute(
        "UPDATE queue_items SET title=? WHERE id=? AND status IN ('queued','picking')",
        (title, item_id),
    )
    con.commit()


def update_queue_desc(con, item_id: int, desc: str):
    con.execute(
        "UPDATE queue_items SET description=? WHERE id=? AND status IN ('queued','picking')",
        (desc, item_id),
    )
    con.commit()


def update_queue_thumb_file_id(con, item_id: int, file_id: str):
    con.execute(
        "UPDATE queue_items SET thumb_mode='custom', manual_thumb_file_id=? "
        "WHERE id=? AND status IN ('queued','picking')",
        (file_id, item_id),
    )
    con.commit()


def list_queued_ids(con, limit: int = 100):
    rows = con.execute(
        "SELECT id FROM queue_items WHERE status='queued' ORDER BY sort_order ASC, id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [int(r["id"]) for r in rows]


def swap_queue_order(con, id1: int, id2: int) -> None:
    r1 = con.execute(
        "SELECT sort_order FROM queue_items WHERE id=? AND status='queued'",
        (id1,),
    ).fetchone()
    r2 = con.execute(
        "SELECT sort_order FROM queue_items WHERE id=? AND status='queued'",
        (id2,),
    ).fetchone()
    if not r1 or not r2:
        return

    o1, o2 = r1["sort_order"], r2["sort_order"]
    con.execute("BEGIN")
    con.execute("UPDATE queue_items SET sort_order=? WHERE id=? AND status='queued'", (o2, id1))
    con.execute("UPDATE queue_items SET sort_order=? WHERE id=? AND status='queued'", (o1, id2))
    con.execute("COMMIT")


def pick_next_for_today(con):
    """
    یک آیتم queued را برمی‌دارد و picked_at می‌زند.
    اگر همزمان دو پردازش تلاش کنند، با UPDATE شرط‌دار از دوباره‌برداشتن جلوگیری می‌کنیم.
    """
    row = con.execute("""
        SELECT id FROM queue_items
        WHERE status='queued'
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
    """).fetchone()
    if not row:
        return None

    item_id = int(row["id"])

    cur = con.execute(
        "UPDATE queue_items SET status='picking', picked_at=datetime('now') "
        "WHERE id=? AND status='queued'",
        (item_id,),
    )
    con.commit()

    # اگر همزمان یکی دیگر زودتر برداشت، این UPDATE هیچ ردیفی را تغییر نمی‌دهد
    if cur.rowcount == 0:
        return None

    return item_id


def mark_back_to_queue(con, item_id: int):
    con.execute("UPDATE queue_items SET status='queued' WHERE id=? AND status='picking'", (item_id,))
    con.commit()


def mark_ready(con, item_id: int):
    con.execute("UPDATE queue_items SET status='ready' WHERE id=? AND status='picking'", (item_id,))
    con.commit()


def get_last_publish_day(con) -> str | None:
    return get_setting(con, "last_publish_day")


def set_last_publish_day(con, day: str):
    set_setting(con, "last_publish_day", day)
