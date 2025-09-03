SYSTEM_PROMPT = (
    "You are a precise news analyst. Extract companies and produce summaries. "
    "Return ONLY valid JSON matching the given schema."
)

JSON_SCHEMA_DESC = {
    "type": "object",
    "properties": {
        "companies_ranked": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "primary_company": {"type": "string"},
        "company_one_liner": {"type": "string"},
        "summary_zh_tw": {"type": "string"},
        "summary_en": {"type": "string"},
    },
    "required": [
        "companies_ranked",
        "keywords",
        "primary_company",
        "company_one_liner",
        "summary_zh_tw",
        "summary_en",
    ],
}

USER_PROMPT_TEMPLATE = (
    "You will read a Taiwanese tech/business news article and output JSON.\n\n"
    "Article Title: {title}\n"
    "Publish Date: {date}\n\n"
    "Full Text (Taiwanese Mandarin):\n{body}\n\n"
    "Instructions:\n"
    "1) List `companies_ranked` (most→least important) using official English or Traditional Chinese names\n"
    "2) `keywords`: 3–5 concise, high-signal keywords (nouns/proper terms). Use Traditional Chinese if the article is Chinese; otherwise English.\n\n"
    "3) Select `primary_company` (must be one of companies_ranked; if none, use 'Unknown')\n"
    "4) `company_one_liner`: one sentence describing primary_company's core business, what it does, and its products/services in Traditional Chinese\n"
    "5) `summary_zh_tw`: detailed Traditional Chinese summary (Taiwanese style)\n"
    "6) `summary_en`: detailed English summary\n\n"
    "Constraints:\n"
    "- Output strictly JSON only, no markdown, no commentary.\n"
    "- Keep names canonical; avoid duplicates or tickers unless necessary.\n"
)