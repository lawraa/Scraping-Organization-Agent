from __future__ import annotations
import json
import re
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


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
        # Simple, robust single-string prompt (matches your working example usage)
        prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + USER_PROMPT_TEMPLATE.format(title=title or "", date=date or "", body=body or "")
        )

        # Primary call path
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            temperature=0,
        )

        text = getattr(resp, "text", None) or ""

        # Fallback: try list-style contents if some SDK variant requires it
        if not text:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": [prompt]}],
            )
            text = getattr(resp, "text", None) or ""

        if not text:
            raise RuntimeError("Gemini returned no text content.")

        # Parse JSON; salvage if fenced or wrapped
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

        # Ensure expected keys exist
        data.setdefault("companies_ranked", [])
        data.setdefault("primary_company", "Unknown")
        data.setdefault("company_one_liner", "")
        data.setdefault("summary_zh_tw", "")
        data.setdefault("summary_en", "")
        return data
