"""
LLM Service — supports Gemini and OpenAI as providers, with built-in intelligent
fallback travel generation for maximum resilience, portfolio demonstration, and testing.
"""
import json
import re
import asyncio
import logging
from typing import Any, Dict, Optional
from app.config import get_settings
from app.services.fallback_generator import generate_fallback_for_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


def _clean_json(text: str) -> str:
    """Strip markdown code fences and whitespace from LLM output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _is_api_key_configured(key: str) -> bool:
    if not key or not key.strip():
        return False
    lower = key.strip().lower()
    if "your_" in lower or "_here" in lower or "placeholder" in lower:
        return False
    return True


class LLMService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self._gemini_client = None
        self._openai_client = None

    def _get_gemini(self):
        if self._gemini_client is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")
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
            if not _is_api_key_configured(settings.GEMINI_API_KEY):
                raise ValueError("GEMINI_API_KEY is not configured")
            return await self._generate_gemini(prompt, system_prompt)
        elif self.provider == "openai":
            if not _is_api_key_configured(settings.OPENAI_API_KEY):
                raise ValueError("OPENAI_API_KEY is not configured")
            return await self._generate_openai(prompt, system_prompt)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a JSON response and parse it.
        If the external AI provider is unavailable, unconfigured, or encounters an error,
        it automatically falls back to the intelligent domain-specific travel generator.
        """
        # Check if API key is configured
        api_configured = (
            (self.provider == "gemini" and _is_api_key_configured(settings.GEMINI_API_KEY)) or
            (self.provider == "openai" and _is_api_key_configured(settings.OPENAI_API_KEY))
        )

        if not api_configured:
            logger.info("API key unconfigured; using intelligent domain fallback generator.")
            return generate_fallback_for_prompt(prompt, system_prompt or "")

        full_prompt = prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, just JSON."
        try:
            raw = await self.generate(full_prompt, system_prompt)
            cleaned = _clean_json(raw)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", cleaned)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"Failed to parse LLM JSON response")
        except Exception as e:
            logger.warning(f"External LLM generation failed ({e}); falling back to intelligent travel generator.")
            return generate_fallback_for_prompt(prompt, system_prompt or "")

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
