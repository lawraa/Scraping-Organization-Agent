from __future__ import annotations
import argparse

from config import DEFAULT_CSV_PATH, PAGES_TO_SCAN, REQUEST_DELAY, GEMINI_API_KEY, GEMINI_MODEL
from crawler import crawl_links
from parser import parse_article_page
from enrich import GeminiEnricher
from storage import init_db, have_article, upsert_article, fetch_all_df
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urlparse, parse_qsl 

CSV_COLS = [
    "article_id", "url", "headline", "publish_date", "keywords",
    "companies_ranked", "primary_company", "company_one_liner",
    "summary_zh_tw", "summary_en", "fetched_at",
]


def export_csv_atomic(csv_path: str) -> int:
    """
    Export the entire DB snapshot to CSV atomically.
    Returns the number of rows written. Writes to *.tmp then replaces.
    """
    df = fetch_all_df()
    if df.empty:
        return 0
    df = df[CSV_COLS]
    tmp = Path(csv_path).with_suffix(Path(csv_path).suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(csv_path) 
    return len(df)

def _article_id_from_url(url: str) -> str | None:  
    qs = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    num = qs.get("num")
    return num if num and num.isdigit() else None

def run_pipeline(max_pages: int, all_pages: bool, do_enrich: bool, csv_path: str):
    init_db()

    print(f"[Crawl] pages = {'ALL' if all_pages else max_pages}, delay={REQUEST_DELAY}s")
    urls = crawl_links(max_pages=max_pages, auto_all=all_pages, delay=REQUEST_DELAY)
    print(f"[Crawl] found {len(urls)} article URLs (deduped)")
    enricher = None
    if do_enrich:
        enricher = GeminiEnricher(api_key=GEMINI_API_KEY, model_name=GEMINI_MODEL)
        print(f"[Gemini] model ready: {GEMINI_MODEL}")
    else:
        print("[Gemini] enrichment disabled (--no-enrich)")

    new_count = 0
    for i, url in enumerate(tqdm(urls, desc="Processing articles", unit="article"), 1):
        aid = _article_id_from_url(url)
        if not aid:
            print(f"[{i:03d}] Skip (no article_id in URL): {url}")
            continue
        if have_article(aid):
            print(f"[{i:03d}] Seen, skip: {aid}")
            continue
        print(f"[{i:03d}] Fetching & parsing: {url}")  
        art = parse_article_page(url)
        body = (art.get("body") or "").strip()
        if len(body) < 10:
            print(f"[{i:03d}] Body too short, skip: {aid}")
            continue
        if enricher:
            try:
                enrich = enricher.enrich(
                    title=art.get("headline"),
                    date=art.get("publish_date"),
                    body=body
                )
            except Exception as e:
                print(f"[{i:03d}] Enrich failed ({aid}): {e}")
                enrich = {
                    "companies_ranked": [],
                    "primary_company": "Unknown",
                    "company_one_liner": "",
                    "summary_zh_tw": "",
                    "summary_en": "",
                }
        else:
            enrich = {
                "companies_ranked": [],
                "primary_company": "Unknown",
                "company_one_liner": "",
                "summary_zh_tw": "",
                "summary_en": "",
            }

        row = {**art, **enrich}
        upsert_article(row)
        new_count += 1
        print(f"[{i:03d}] Added: {aid} | {art.get('headline')}")

        try:
            n = export_csv_atomic(csv_path)
            print(f"[Export] Checkpoint CSV ({n} rows) → {csv_path}")
        except Exception as e:
            print(f"[Export] CSV checkpoint failed: {e}")

    try:
        n = export_csv_atomic(csv_path)
        if n:
            print(f"[Export] Final CSV ({n} rows) → {csv_path}")
        else:
            print("[Export] No rows in DB yet. Skipping CSV.")
    except Exception as e:
        print(f"[Export] Final CSV export failed: {e}")

    print(f"[Done] New rows this run: {new_count}")




if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="GBI Monthly → Gemini → CSV pipeline")
    ap.add_argument("--all", action="store_true", help="Crawl ALL pages (could be heavy)")
    ap.add_argument("--max-pages", type=int, default=PAGES_TO_SCAN, help="How many index pages to scan if not --all")
    ap.add_argument("--no-enrich", action="store_true", help="Skip Gemini enrichment (crawl/parse only)")
    ap.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Output .csv path (overwrites)")
    args = ap.parse_args()

    run_pipeline(
        max_pages=args.max_pages,
        all_pages=args.all,
        do_enrich=not args.no_enrich,
        csv_path=args.csv,
    )