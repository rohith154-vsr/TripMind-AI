"""
LLM Service — supports Gemini and OpenAI as providers.
All agents call this service for AI reasoning.
"""
import json
import re
import asyncio
from typing import Any, Dict, Optional
from app.config import get_settings

settings = get_settings()


def _clean_json(text: str) -> str:
    """Strip markdown code fences and whitespace from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


class LLMService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self._gemini_client = None
        self._openai_client = None

    def _get_gemini(self):
        if self._gemini_client is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL)
        return self._gemini_client

    def _get_openai(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a text response from the configured LLM provider."""
        if self.provider == "gemini":
            return await self._generate_gemini(prompt, system_prompt)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, system_prompt)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate a JSON response and parse it."""
        full_prompt = prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, just JSON."
        raw = await self.generate(full_prompt, system_prompt)
        cleaned = _clean_json(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Failed to parse LLM JSON response: {e}\nRaw: {cleaned[:500]}")

    async def _generate_gemini(self, prompt: str, system_prompt: Optional[str]) -> str:
        model = self._get_gemini()
        full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(full)
        )
        return response.text

    async def _generate_openai(self, prompt: str, system_prompt: Optional[str]) -> str:
        client = self._get_openai()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            timeout=settings.LLM_TIMEOUT,
        )
        return response.choices[0].message.content or ""


# Singleton
llm_service = LLMService()
