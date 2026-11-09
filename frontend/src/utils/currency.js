/**
 * Currency Formatting Utilities
 * Provides standardized currency display and admission fee formatting
 * with strict currency pair matching and preservation of original denominations.
 */

/**
 * Format numeric currency amounts with standardized symbols and locale formatting.
 *
 * @param {number|string} amount - Monetary amount to format
 * @param {string} currency - 3-letter ISO currency code (default: 'USD')
 * @returns {string} Formatted currency string or '—' if invalid/null
 */
export function formatCurrency(amount, currency = 'USD') {
  if (amount == null || String(amount).trim() === '' || isNaN(Number(amount))) {
    return '—'
  }
  const curr = (currency || 'USD').toUpperCase()
  const symbols = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    INR: '₹',
    JPY: '¥',
    CAD: 'CA$',
    AUD: 'AU$',
  }
  const sym = symbols[curr] || `${curr} `
  return `${sym}${Number(amount).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

/**
 * Formats attraction admission fees with transparency, showing converted target amounts
 * alongside original fee denominations, and strictly enforcing currency pair verification.
 *
 * @param {Object} attr - Attraction object with admission_fee, admission_fee_currency, or admission_fee_usd
 * @param {string} tripCurrency - Target trip currency code (default: 'USD')
 * @param {Object|number|null} currencyConversion - Currency conversion rate metadata
 * @returns {string|null} Formatted admission fee string or null if fee is missing
 */
export function formatAdmissionFee(attr, tripCurrency = 'USD', currencyConversion = null) {
  if (!attr || typeof attr !== 'object') return null

  // Free admissions
  if (attr.admission_fee === 0 || attr.admission_fee_usd === 0) {
    return '🆓 Free'
  }

  const targetCurr = (tripCurrency || 'USD').toUpperCase()

  // Helper to extract verified conversion rate strictly for this specific currency pair
  const getVerifiedRate = (fromCurr, toCurr) => {
    if (!currencyConversion) return null

    // If currencyConversion is a structured object with source and target
    if (typeof currencyConversion === 'object' && currencyConversion !== null) {
      const orig = (currencyConversion.original_currency || '').toUpperCase()
      const target = (currencyConversion.target_currency || '').toUpperCase()
      const rate = currencyConversion.exchange_rate
      if (orig === fromCurr && target === toCurr && typeof rate === 'number' && rate > 0) {
        return rate
      }
      return null // Mismatched pair! Reject applying unrelated exchange rates
    }

    // Legacy fallback: if a raw numeric rate was passed, only allow if fromCurr is USD
    if (typeof currencyConversion === 'number' && currencyConversion > 0 && fromCurr === 'USD') {
      return currencyConversion
    }
    return null
  }

  // 1. If explicit native admission_fee and admission_fee_currency are present
  if (attr.admission_fee != null && attr.admission_fee_currency) {
    const feeCurr = attr.admission_fee_currency.toUpperCase()
    if (feeCurr === targetCurr) {
      return `💰 ${formatCurrency(attr.admission_fee, targetCurr)}`
    }
    // Check if conversion rate exists specifically for feeCurr -> targetCurr
    const rate = getVerifiedRate(feeCurr, targetCurr)
    if (rate != null) {
      const converted = Math.round(attr.admission_fee * rate)
      return `💰 ${formatCurrency(converted, targetCurr)} (${formatCurrency(attr.admission_fee, feeCurr)})`
    }
    // Preserves original currency clearly if conversion is unavailable or currencies mismatch
    return `💰 ${formatCurrency(attr.admission_fee, feeCurr)}`
  }

  // 2. If admission_fee_usd is present
  if (attr.admission_fee_usd != null) {
    if (targetCurr === 'USD') {
      return `💰 $${attr.admission_fee_usd}`
    }
    const rate = getVerifiedRate('USD', targetCurr)
    if (rate != null) {
      const converted = Math.round(attr.admission_fee_usd * rate)
      return `💰 ${formatCurrency(converted, targetCurr)} ($${attr.admission_fee_usd} USD)`
    }
    // Preserves original USD currency if conversion unavailable
    return `💰 $${attr.admission_fee_usd} USD`
  }

  // 3. Fallback for unlabelled numeric fee
  if (attr.admission_fee != null && !isNaN(Number(attr.admission_fee))) {
    return `💰 ${formatCurrency(attr.admission_fee, targetCurr)}`
  }

  return null
}

