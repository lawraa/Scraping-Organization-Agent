from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import pandas as pd
from config import DB_PATH
import json
from typing import Iterable

def delete_article_by_id(article_id: str) -> int:
    """Delete a single article. Returns number of rows deleted (0 or 1)."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM articles WHERE article_id = ?", (article_id,))
        return cur.rowcount or 0

def delete_articles(ids: Iterable[str]) -> int:
    """Delete multiple article_ids. Returns number of rows deleted."""
    ids = [str(x).strip() for x in ids if str(x).strip()]
    if not ids:
        return 0
    placeholders = ",".join(["?"] * len(ids))
    with get_conn() as conn:
        cur = conn.execute(f"DELETE FROM articles WHERE article_id IN ({placeholders})", ids)
        return cur.rowcount or 0

def _companies_to_str(cell):
    try:
        arr = json.loads(cell) if cell else []
    except Exception:
        # if it's already a Python object (rare) or invalid JSON, stringify
        return str(cell)

    names = []
    for item in arr:
        if isinstance(item, str):
            s = item.strip()
        elif isinstance(item, dict):
            # prefer common name keys; fallback to str(dict)
            for k in ("name", "company", "org", "value", "text", "title"):
                v = item.get(k)
                if isinstance(v, str) and v.strip():
                    s = v.strip()
                    break
            else:
                s = str(item).strip()
        else:
            s = str(item).strip()
        if s:
            names.append(s)

    # de-dup while preserving order
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return ", ".join(out)


@contextmanager
def get_conn(db_path: Path | str = DB_PATH):
    conn = sqlite3.connect(str(db_path))
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
              article_id TEXT PRIMARY KEY,
              url TEXT,
              headline TEXT,
              publish_date TEXT,
              body TEXT,
              companies_ranked TEXT,  -- JSON array
              primary_company TEXT,
              company_one_liner TEXT,
              summary_zh_tw TEXT,
              summary_en TEXT,
              fetched_at TEXT DEFAULT (datetime('now'))
            );
            """
        )


def have_article(article_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("SELECT 1 FROM articles WHERE article_id = ? LIMIT 1", (article_id,))
        return cur.fetchone() is not None


def upsert_article(row: dict):
    # Ensure JSON serialization for list fields
    companies_json = json.dumps(row.get("companies_ranked") or [], ensure_ascii=False)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO articles (
              article_id, url, headline, publish_date, body,
              companies_ranked, primary_company, company_one_liner,
              summary_zh_tw, summary_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_id) DO UPDATE SET
              url=excluded.url,
              headline=excluded.headline,
              publish_date=excluded.publish_date,
              body=excluded.body,
              companies_ranked=excluded.companies_ranked,
              primary_company=excluded.primary_company,
              company_one_liner=excluded.company_one_liner,
              summary_zh_tw=excluded.summary_zh_tw,
              summary_en=excluded.summary_en
            ;
            """,
            (
                row.get("article_id"), row.get("url"), row.get("headline"), row.get("publish_date"), row.get("body"),
                companies_json, row.get("primary_company"), row.get("company_one_liner"),
                row.get("summary_zh_tw"), row.get("summary_en"),
            ),
        )


def fetch_all_df() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT article_id, url, headline, publish_date, "
            "companies_ranked, primary_company, company_one_liner, summary_zh_tw, summary_en, fetched_at "
            "FROM articles ORDER BY publish_date DESC NULLS LAST, fetched_at DESC",
            conn,
        )
    # Parse companies JSON
    if not df.empty and "companies_ranked" in df.columns:
        df["companies_ranked"] = df["companies_ranked"].apply(_companies_to_str)
    return df

