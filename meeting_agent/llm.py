from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import Settings


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.deepseek_api_key:
            raise ValueError("Missing DEEPSEEK_API_KEY. Set it in .env or your shell environment.")

        self.model = settings.deepseek_model
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def complete(self, system_prompt: str, user_content: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


def parse_json_array(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []

    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, dict)]
