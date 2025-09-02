from __future__ import annotations
import re
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qsl

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from config import USER_AGENT, DEFAULT_TIMEOUT

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
})

DATE_LABEL_RE = re.compile(r"(?:發佈日期|發布日期|日期)\s*[:：]?\s*", re.I)
DATE_VALUE_RE = re.compile(r"\b(\d{4}[/-]\d{2}[/-]\d{2})\b")
STOP_TOKENS_RE = re.compile(r"(編輯推薦|延伸閱讀|當期雜誌|影音專區|參考資料|回列表頁|TOP|©)", re.I)

ARTICLE_BODY_SELECTORS = [
    'div.editor.fsize_area[itemprop="articleBody"]',
    '.editor.fsize_area[itemprop="articleBody"]',
]
EXCLUDE_INSIDE_EDITOR = [
    "div.copyright",
    "div.tagBox",
    "div.recommend",
    "div.reporter-con",
    "div.nextBox",
    "div.read",
    "div.sub-btn",
    "div.adBox",
]

EXCLUDE_SELECTORS = [
    "header", "nav", "footer", "aside",
    "ul.pager", "div.pager",
    "div#footer", "div.footer",
    "div.share", "div.social",
    "div.breadcrumb", "ol.breadcrumb",
    "div.related", "section.related",
    "div#sidebar", ".sidebar",
]


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _get_article_id(url: str) -> Optional[str]:
    qs = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    num = qs.get("num")
    return num if num and num.isdigit() else None


def fetch_article_html(url: str) -> str:
    r = session.get(url, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def _extract_headline(soup: BeautifulSoup) -> Optional[str]:
    tb = soup.select_one("div.titleBox > h1")
    if tb:
        t = _strip(tb.get_text(" "))
        if t:
            return t
    for sel in ["article h1", "main h1", "h1", "h2"]:
        el = soup.select_one(sel)
        if el:
            t = _strip(el.get_text(" "))
            if t and len(t) >= 6:
                return t
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "strong", "b"]):
        t = _strip(tag.get_text(" "))
        if t and len(t) >= 6:
            candidates.append(t)
    return max(candidates, key=len) if candidates else None


def _extract_date(soup: BeautifulSoup) -> Optional[str]:
    d = soup.select_one("div.reporter div.date")
    if d:
        m = DATE_VALUE_RE.search(_strip(d.get_text(" ")))
        if m:
            return m.group(1).replace("/", "-")
    for node in soup.find_all(string=DATE_LABEL_RE):
        context = node.parent.get_text(" ", strip=True) if isinstance(node, NavigableString) else str(node)
        m = DATE_VALUE_RE.search(context)
        if m:
            return m.group(1).replace("/", "-")
    for sel in [
        'meta[property="article:published_time"]',
        'meta[name="pubdate"]',
        'meta[itemprop="datePublished"]',
        'meta[name="date"]',
    ]:
        meta = soup.select_one(sel)
        if meta and meta.get("content"):
            m = DATE_VALUE_RE.search(meta["content"])
            if m:
                return m.group(1).replace("/", "-")
    for near in soup.select("h1, h2, .title, .post-meta, .meta"):
        txt = _strip(near.get_text(" "))
        m = DATE_VALUE_RE.search(txt)
        if m:
            return m.group(1).replace("/", "-")
    return None


def _looks_like_chrome(tag: Tag) -> bool:
    if tag.name in {"header", "nav", "footer", "aside"}:
        return True
    class_id = " ".join((tag.get("class") or []) + [tag.get("id") or ""]).lower()
    for kw in ["header", "nav", "footer", "aside", "sidebar", "breadcrumb", "pager", "login", "member"]:
        if kw in class_id:
            return True
    return False


def _candidate_blocks(soup: BeautifulSoup):
    for sel in EXCLUDE_SELECTORS:
        for n in soup.select(sel):
            n.decompose()
    cands = []
    for container in soup.find_all(["article", "section", "div"], recursive=True):
        if _looks_like_chrome(container):
            continue
        txt = _strip(container.get_text(" "))
        if len(txt) >= 200 and sum(map(str.isalnum, txt)) > 80:
            pcount = len(container.find_all("p"))
            score = len(txt) + 50 * pcount
            cands.append((score, container))
    cands.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in cands[:6]]


def _collect_text_from_container(node: Tag) -> str:
    parts = []
    for p in node.find_all("p"):
        t = _strip(p.get_text(" "))
        if t and len(t) >= 10 and not STOP_TOKENS_RE.search(t):
            parts.append(t)
    if sum(len(x) for x in parts) < 300:
        for el in node.descendants:
            if isinstance(el, NavigableString):
                t = _strip(str(el))
                if t and not STOP_TOKENS_RE.search(t):
                    parts.append(t)
            elif isinstance(el, Tag) and el.name.lower() == "br":
                parts.append("\n")
    text = "\n\n".join([p for p in parts if p.strip()])
    text = re.sub(r"(A\+|A\-|加入收藏|Select Language)\s*", "", text)
    return text.strip()


def _extract_body_from_editor(soup: BeautifulSoup) -> str:
    container = None
    for sel in ARTICLE_BODY_SELECTORS:
        container = soup.select_one(sel)
        if container:
            break
    if not container:
        return ""
    for sel in EXCLUDE_INSIDE_EDITOR:
        for n in container.select(sel):
            n.decompose()
    parts = []
    for node in container.descendants:
        if isinstance(node, NavigableString):
            t = _strip(str(node))
            if t:
                parts.append(t)
        elif isinstance(node, Tag) and node.name.lower() == "br":
            parts.append("\n")
    text = "".join(parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(A\+|A\-|加入收藏|Select Language)\s*", "", text)
    for tok in ["參考資料：", "(編譯", "©", "All rights reserved"]:
        idx = text.find(tok)
        if idx != -1 and idx > 300:
            text = text[:idx].rstrip()
            break
    return text.strip()


def _extract_body(soup: BeautifulSoup) -> str:
    body = _extract_body_from_editor(soup)
    if len(body) >= 200 and re.search(r"[。！？.!?]", body):
        return body
    for cont in _candidate_blocks(soup):
        body = _collect_text_from_container(cont)
        if len(body) >= 400 and re.search(r"[。！？.!?]", body):
            return body
    whole = _collect_text_from_container(soup.body or soup)
    return whole


def parse_article_page(url: str) -> Dict[str, str | None]:
    html = fetch_article_html(url)
    soup = BeautifulSoup(html, "html.parser")
    return {
        "article_id": _get_article_id(url),
        "url": url,
        "headline": _extract_headline(soup),
        "publish_date": _extract_date(soup),
        "body": _extract_body(soup),
    }