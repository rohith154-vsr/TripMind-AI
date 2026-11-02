"""
Currency Service — uses Frankfurter API (free, no key required).
https://www.frankfurter.app/
"""
import httpx
from typing import Dict, Optional
from app.config import get_settings

settings = get_settings()

FRANKFURTER_URL = "https://api.frankfurter.app"


async def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """Get the exchange rate from one currency to another."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    url = f"{FRANKFURTER_URL}/latest"
    params = {"from": from_currency, "to": to_currency}
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        return rates.get(to_currency)


async def convert_amount(amount: float, from_currency: str, to_currency: str) -> Optional[Dict]:
    """Convert an amount and return detailed info."""
    rate = await get_exchange_rate(from_currency, to_currency)
    if rate is None:
        return None
    return {
        "original_amount": amount,
        "original_currency": from_currency.upper(),
        "converted_amount": round(amount * rate, 2),
        "target_currency": to_currency.upper(),
        "exchange_rate": rate,
    }


async def get_supported_currencies() -> Dict[str, str]:
    """Return a dict of supported currency codes → names."""
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(f"{FRANKFURTER_URL}/currencies")
        resp.raise_for_status()
        return resp.json()
