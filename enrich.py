from __future__ import annotations
import json
import re
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def _to_string_list(x):
    if isinstance(x, list):
        out = []
        for item in x:
            if isinstance(item, str):
                out.append(item.strip())
            elif isinstance(item, dict):
                for k in ("name", "keyword", "company", "org", "value", "text", "title"):
                    v = item.get(k)
                    if isinstance(v, str) and v.strip():
                        out.append(v.strip())
                        break
                else:
                    out.append(str(item).strip())
            else:
                out.append(str(item).strip())
        seen, dedup = set(), []
        for s in out:
            if s and s not in seen:
                seen.add(s)
                dedup.append(s)
        return dedup
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    return []


class GeminiEnricher:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        api_key = api_key or GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required. Set it in .env or env.")
        self.client = genai.Client(api_key=api_key)
        self.model = (model_name or GEMINI_MODEL).strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    def enrich(self, *, title: str | None, date: str | None, body: str) -> dict:
        prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + USER_PROMPT_TEMPLATE.format(title=title or "", date=date or "", body=body or "")
        )

        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = getattr(resp, "text", "") or ""

        if not text:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": [prompt]}]
            )
            text = getattr(resp, "text", "") or ""

        if not text:
            raise RuntimeError("Gemini returned no text content.")

        raw = text.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raw2 = raw.strip("` ")
            try:
                data = json.loads(raw2)
            except json.JSONDecodeError:
                m = re.search(r"\{[\s\S]*\}", raw)
                if not m:
                    raise
                data = json.loads(m.group(0))

        # Defaults
        data.setdefault("companies_ranked", [])
        data.setdefault("keywords", [])
        data.setdefault("primary_company", "Unknown")
        data.setdefault("company_one_liner", "")
        data.setdefault("summary_zh_tw", "")
        data.setdefault("summary_en", "")

        companies = _to_string_list(data.get("companies_ranked", []))
        data["companies_ranked"] = companies
        keywords = _to_string_list(data.get("keywords", []))
        data["keywords"] = keywords[:5]  # keep at most 5

        pc = data.get("primary_company")
        if isinstance(pc, dict):
            for k in ("name", "company", "org", "value", "text", "title"):
                v = pc.get(k)
                if isinstance(v, str) and v.strip():
                    pc = v.strip()
                    break
            else:
                pc = str(pc).strip()
        if not isinstance(pc, str) or not pc.strip():
            pc = companies[0] if companies else "Unknown"
        data["primary_company"] = pc

        return data
