from __future__ import annotations
import argparse
from pathlib import Path

from config import DEFAULT_CSV_PATH
from storage import delete_article_by_id, delete_articles, fetch_all_df

import sys
sys.argv = ["manage.py", "delete", "--ids", "80108"]

CSV_COLS = [
    "article_id", "url", "headline", "publish_date",
    "companies_ranked", "primary_company", "company_one_liner",
    "summary_zh_tw", "summary_en", "fetched_at",
]

def export_csv_atomic(csv_path: str) -> int:
    df = fetch_all_df()
    if df.empty:
        return 0
    df = df[CSV_COLS]
    tmp = Path(csv_path).with_suffix(Path(csv_path).suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(csv_path)
    return len(df)

def parse_ids_arg(ids_arg: str | None, from_file: str | None) -> list[str]:
    ids: list[str] = []
    if ids_arg:
        ids += [x.strip() for x in ids_arg.split(",") if x.strip()]
    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            ids += [line.strip() for line in f if line.strip()]
    # de-dup, keep order
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i); out.append(i)
    return out

def main():
    ap = argparse.ArgumentParser(description="Manage the articles DB")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_del = sub.add_parser("delete", help="Delete article(s) by ID")
    sp_del.add_argument("--ids", help="Comma-separated IDs, e.g. 80098,80123")
    sp_del.add_argument("--from-file", help="Text file with one ID per line")
    sp_del.add_argument("--csv", default=str(DEFAULT_CSV_PATH),
                        help="CSV path to refresh after deletion (default: config.DEFAULT_CSV_PATH)")
    sp_del.add_argument("--no-export", action="store_true", help="Do not rewrite the CSV snapshot")

    args = ap.parse_args()

    if args.cmd == "delete":
        ids = parse_ids_arg(args.ids, args.from_file)
        if not ids:
            print("No IDs provided. Use --ids or --from-file.")
            return
        deleted = delete_articles(ids) if len(ids) > 1 else delete_article_by_id(ids[0])
        print(f"Deleted {deleted} row(s) from DB.")

        if not args.no_export:
            n = export_csv_atomic(args.csv)
            print(f"Refreshed CSV snapshot → {args.csv} ({n} rows)")

if __name__ == "__main__":
    main()
