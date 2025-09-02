from __future__ import annotations
import time
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup

from config import BASE_INDEX_URL, USER_AGENT, REQUEST_DELAY

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
})


def _normalize_article_url(href: str) -> str:
    abs_url = urljoin(BASE_INDEX_URL, href)
    u = urlparse(abs_url)
    qs = dict(parse_qsl(u.query, keep_blank_values=True))
    new_qs = {"num": qs["num"]} if "num" in qs else {}
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(new_qs, doseq=True), ""))


def _is_news_article_href(href: str) -> bool:
    abs_url = urljoin(BASE_INDEX_URL, href)
    u = urlparse(abs_url)
    if u.path != "/tw/article/show.php":
        return False
    qs = dict(parse_qsl(u.query, keep_blank_values=True))
    num = qs.get("num")
    return bool(num and num.isdigit())


def fetch_index_html(page: int | None) -> tuple[str, str]:
    url = BASE_INDEX_URL if (page is None or page == 1) else f"{BASE_INDEX_URL}?page={page}"
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return url, r.text


def parse_article_links(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        if _is_news_article_href(href):
            found.append(_normalize_article_url(href))
    uniq, seen = [], set()
    for u in found:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq


def parse_pager(index_html: str) -> dict:
    soup = BeautifulSoup(index_html, "html.parser")
    pager = soup.find("ul", class_="pager")
    out = {"next_page": None, "last_page": None, "pages_in_nav": []}
    if not pager:
        return out

    for a in pager.find_all("a", href=True):
        href = a["href"]
        if "page=" in href and a.get_text(strip=True).isdigit():
            try:
                out["pages_in_nav"].append(int(href.split("page=")[-1]))
            except ValueError:
                pass

    a_next = pager.find("a", class_="next")
    if a_next and "page=" in a_next.get("href", ""):
        try:
            out["next_page"] = int(a_next["href"].split("page=")[-1])
        except ValueError:
            pass

    a_last = pager.find("a", class_="last")
    if a_last and "page=" in a_last.get("href", ""):
        try:
            out["last_page"] = int(a_last["href"].split("page=")[-1])
        except ValueError:
            pass

    return out


def crawl_links(max_pages: int, auto_all: bool = False, delay: float = REQUEST_DELAY) -> list[str]:
    all_urls, seen = [], set()
    current_page, pages_crawled = 1, 0
    last_page_limit = None

    while True:
        if not auto_all and pages_crawled >= max_pages:
            break
        _, html = fetch_index_html(current_page)
        links = parse_article_links(html)
        for u in links:
            if u not in seen:
                all_urls.append(u)
                seen.add(u)
        pages_crawled += 1

        pager_info = parse_pager(html)
        if auto_all and last_page_limit is None and pager_info.get("last_page"):
            last_page_limit = pager_info["last_page"]
        next_p = pager_info.get("next_page")

        if next_p:
            if auto_all and last_page_limit is not None and current_page >= last_page_limit:
                break
            current_page = next_p
            time.sleep(delay)
        else:
            break

    return all_urls