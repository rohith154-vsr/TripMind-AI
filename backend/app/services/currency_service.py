"""
Currency Service — uses Frankfurter API (free, no key required) with
in-memory caching, fallback conversion estimation, and explicit rate provenance labelling.
https://www.frankfurter.app/
"""
import time
import httpx
from typing import Dict, Optional, Tuple, Any
from app.config import get_settings

settings = get_settings()

FRANKFURTER_URL = "https://api.frankfurter.dev/v1"

# In-memory cache: (from_curr, to_curr) -> (rate, timestamp)
_RATE_CACHE: Dict[Tuple[str, str], Tuple[float, float]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

# Static fallback exchange rates relative to 1 USD for graceful degradation
# Note: These are strictly labeled as estimated fallback rates, never as live rates.
ESTIMATED_USD_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 86.5,
    "JPY": 152.0,
    "CAD": 1.38,
    "AUD": 1.52,
    "CHF": 0.88,
    "CNY": 7.24,
    "SGD": 1.34,
    "AED": 3.67,
    "THB": 34.5,
}


async def get_exchange_rate_with_metadata(from_currency: str, to_currency: str) -> Tuple[Optional[float], bool, str]:
    """
    Get exchange rate between two currencies with provenance metadata.
    Returns: (rate, is_live_rate, source_label)
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()

    if from_curr == to_curr:
        return 1.0, True, "Identical currency (1:1)"

    cache_key = (from_curr, to_curr)
    now = time.time()

    # Check cache first
    if cache_key in _RATE_CACHE:
        rate, timestamp = _RATE_CACHE[cache_key]
        if now - timestamp < CACHE_TTL_SECONDS:
            return rate, True, "Frankfurter API (Cached)"

    # Try live Frankfurter API
    try:
        url = f"{FRANKFURTER_URL}/latest"
        params = {"from": from_curr, "to": to_curr}
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                rate = rates.get(to_curr)
                if rate is not None:
                    rate_val = float(rate)
                    _RATE_CACHE[cache_key] = (rate_val, now)
                    return rate_val, True, "Frankfurter API (Live)"
    except Exception:
        # Network or timeout failure, proceed to estimated fallback
        pass

    # Fallback to estimated cross-rate if both currencies are in ESTIMATED_USD_RATES
    if from_curr in ESTIMATED_USD_RATES and to_curr in ESTIMATED_USD_RATES:
        usd_to_from = ESTIMATED_USD_RATES[from_curr]
        usd_to_to = ESTIMATED_USD_RATES[to_curr]
        est_rate = round(usd_to_to / usd_to_from, 4)
        return est_rate, False, "Estimated Fallback Rate (Frankfurter API unavailable)"

    return None, False, "Exchange rate unavailable"


async def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Standard exchange rate function returning a float value for backward compatibility.
    """
    rate, _, _ = await get_exchange_rate_with_metadata(from_currency, to_currency)
    return rate


async def convert_amount(amount: float, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
    """
    Convert an amount and return comprehensive conversion info with provenance.
    """
    rate, is_live, source_label = await get_exchange_rate_with_metadata(from_currency, to_currency)
    if rate is None:
        return None

    return {
        "original_amount": amount,
        "original_currency": from_currency.upper().strip(),
        "converted_amount": round(amount * rate, 2),
        "target_currency": to_currency.upper().strip(),
        "exchange_rate": rate,
        "is_live_rate": is_live,
        "is_estimated": not is_live,
        "rate_source": source_label,
        "notes": None if is_live else "Estimated rate. Live exchange rate could not be verified.",
    }


async def get_supported_currencies() -> Dict[str, str]:
    """Return a dict of supported currency codes -> names."""
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(f"{FRANKFURTER_URL}/currencies")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    # Basic fallback dictionary
    return {
        "USD": "United States Dollar",
        "EUR": "Euro",
        "GBP": "British Pound",
        "INR": "Indian Rupee",
        "JPY": "Japanese Yen",
        "CAD": "Canadian Dollar",
        "AUD": "Australian Dollar",
    }
