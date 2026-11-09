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

# In-memory cache: (from_curr, to_curr) -> (rate, is_live_rate, source_label, timestamp)
_RATE_CACHE: Dict[Tuple[str, str], Tuple[float, bool, str, float]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour for live rates
CACHE_TTL_FALLBACK = 300   # 5 minutes for fallback estimates

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
        rate, is_live, source, timestamp = _RATE_CACHE[cache_key]
        ttl = CACHE_TTL_SECONDS if is_live else CACHE_TTL_FALLBACK
        if now - timestamp < ttl:
            cached_source = f"{source} (Cached)" if "Cached" not in source else source
            return rate, is_live, cached_source

    # Try live Frankfurter API with responsive timeout
    http_timeout = min(float(settings.HTTP_TIMEOUT), 5.0)
    try:
        url = f"{FRANKFURTER_URL}/latest"
        params = {"from": from_curr, "to": to_curr}
        async with httpx.AsyncClient(timeout=http_timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                rate = rates.get(to_curr)
                if rate is not None:
                    rate_val = float(rate)
                    source_label = "Frankfurter API (Live)"
                    _RATE_CACHE[cache_key] = (rate_val, True, source_label, now)
                    return rate_val, True, source_label
    except Exception:
        # Network or timeout failure, proceed to estimated fallback
        pass

    # Fallback to estimated cross-rate if both currencies are in ESTIMATED_USD_RATES
    if from_curr in ESTIMATED_USD_RATES and to_curr in ESTIMATED_USD_RATES:
        usd_to_from = ESTIMATED_USD_RATES[from_curr]
        usd_to_to = ESTIMATED_USD_RATES[to_curr]
        est_rate = round(usd_to_to / usd_to_from, 4)
        source_label = "Estimated Fallback Rate (Frankfurter API unavailable)"
        _RATE_CACHE[cache_key] = (est_rate, False, source_label, now)
        return est_rate, False, source_label

    return None, False, "Exchange rate unavailable"


async def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Standard exchange rate function returning a float value for backward compatibility.
    """
    rate, _, _ = await get_exchange_rate_with_metadata(from_currency, to_currency)
    return rate


async def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    preserve_on_error: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Convert an amount and return comprehensive conversion info with provenance.
    Explicitly tracks source and target currencies.
    If conversion rate is unavailable and preserve_on_error is True,
    returns the original amount preserving the original currency.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    rate, is_live, source_label = await get_exchange_rate_with_metadata(from_curr, to_curr)

    if rate is None:
        if not preserve_on_error:
            return None
        return {
            "original_amount": amount,
            "original_currency": from_curr,
            "converted_amount": amount,
            "target_currency": to_curr,
            "exchange_rate": None,
            "is_live_rate": False,
            "is_estimated": False,
            "rate_source": source_label,
            "conversion_successful": False,
            "preserved_original": True,
            "notes": f"Exchange rate from {from_curr} to {to_curr} unavailable; original currency preserved.",
        }

    return {
        "original_amount": amount,
        "original_currency": from_curr,
        "converted_amount": round(amount * rate, 2),
        "target_currency": to_curr,
        "exchange_rate": rate,
        "is_live_rate": is_live,
        "is_estimated": not is_live,
        "rate_source": source_label,
        "conversion_successful": True,
        "preserved_original": False,
        "notes": None if is_live else f"Estimated fallback cross-rate ({from_curr}->{to_curr}).",
    }


async def get_supported_currencies() -> Dict[str, str]:
    """Return a dict of supported currency codes -> names."""
    http_timeout = min(float(settings.HTTP_TIMEOUT), 5.0)
    try:
        async with httpx.AsyncClient(timeout=http_timeout, follow_redirects=True) as client:
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
