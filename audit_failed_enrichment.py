from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

# Columns we expect in the CSV
REQUIRED_COLS = [
    "article_id", "primary_company", "company_one_liner",
    "summary_zh_tw", "summary_en", "keywords", "companies_ranked",
]

def _as_str(x) -> str:
    if x is None:
        return ""
    s = str(x)
    # Strip BOM or weird whitespace
    return s.replace("\ufeff", "").strip()

def _is_empty_text(x: str) -> bool:
    """
    True if the cell is effectively empty:
    - empty string, whitespace, NaN-ish
    - literal '[]' / '{}' (sometimes sneaks in if JSON not stringified)
    """
    if x is None:
        return True
    s = _as_str(x)
    if s == "":
        return True
    # Handle JSON-looking empties
    empties = {"[]", "{}", '[""]', "['']", "[ ]", "{ }"}
    return s in empties

def _is_empty_list_like(x: str) -> bool:
    """
    For list-like columns exported as a comma-separated string:
    - Empty if blank
    - Empty if it's JSON empty ([], {})
    - Empty if after splitting by comma, nothing meaningful remains
    """
    s = _as_str(x)
    if _is_empty_text(s):
        return True
    # If it looks like JSON list, do a quick-and-dirty strip
    if (s.startswith("[") and s.endswith("]")) or ("," in s):
        parts = [p.strip().strip('\'" []{}') for p in s.split(",")]
        parts = [p for p in parts if p]
        return len(parts) == 0
    return False

def find_failed_ids(df: pd.DataFrame) -> list[str]:
    # Defensive: ensure required columns exist
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV is missing columns: {missing}")

    failed_ids: list[str] = []

    for _, row in df.iterrows():
        aid = _as_str(row.get("article_id"))
        if not aid:
            continue  # skip rows with no id

        primary_company = _as_str(row.get("primary_company"))
        company_one_liner = _as_str(row.get("company_one_liner"))
        summary_zh_tw = _as_str(row.get("summary_zh_tw"))
        summary_en = _as_str(row.get("summary_en"))
        keywords = _as_str(row.get("keywords"))
        companies_ranked = _as_str(row.get("companies_ranked"))

        # Failure heuristics:
        # - primary_company is 'Unknown' or empty
        missing_pc = (primary_company.lower() == "unknown") or _is_empty_text(primary_company)

        # - company_one_liner explicitly set to 'Unknown' (per your note) or empty
        missing_one_liner = (company_one_liner.lower() == "unknown") or _is_empty_text(company_one_liner)

        # - summaries empty
        missing_zh = _is_empty_text(summary_zh_tw)
        missing_en = _is_empty_text(summary_en)

        # - list-like fields empty
        missing_keywords = _is_empty_list_like(keywords)
        missing_companies = _is_empty_list_like(companies_ranked)

        if missing_pc or missing_one_liner or missing_zh or missing_en or missing_keywords or missing_companies:
            failed_ids.append(aid)

    # de-dup while preserving order
    seen, out = set(), []
    for x in failed_ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def main():
    ap = argparse.ArgumentParser(description="Find article_ids with failed/empty enrichment and write to a txt file.")
    ap.add_argument("csv_path", help="Path to articles.csv")
    ap.add_argument("out_txt", help="Output txt file with one article_id per line")
    args = ap.parse_args()

    csv_path = Path(args.csv_path)
    out_txt = Path(args.out_txt)

    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    # Keep strings as strings, avoid NA auto-conversion
    df = pd.read_csv(csv_path, dtype={"article_id": str}, keep_default_na=False, encoding="utf-8-sig")

    ids = find_failed_ids(df)
    if not ids:
        print("No failed rows detected.")
        # Still write an empty file so downstream scripts don't break
        out_txt.write_text("", encoding="utf-8")
        return

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("\n".join(ids) + "\n", encoding="utf-8")
    print(f"Wrote {len(ids)} article_id(s) → {out_txt}")

if __name__ == "__main__":
    main()
