import { describe, it, expect } from 'vitest'
import { formatCurrency, formatAdmissionFee } from './currency.js'

describe('formatCurrency', () => {
  it('formats INR amounts with rupee symbol', () => {
    const formatted = formatCurrency(1500, 'INR')
    expect(formatted).toContain('₹')
    expect(formatted).toContain('1,500')
  })

  it('formats USD amounts with dollar symbol', () => {
    expect(formatCurrency(250, 'USD')).toBe('$250')
    expect(formatCurrency(250)).toBe('$250') // default currency is USD
  })

  it('formats EUR amounts with euro symbol', () => {
    expect(formatCurrency(85, 'EUR')).toBe('€85')
  })

  it('formats GBP amounts with pound symbol', () => {
    expect(formatCurrency(120, 'GBP')).toBe('£120')
  })

  it('handles unknown currency code by prefixing the code with space', () => {
    expect(formatCurrency(500, 'THB')).toBe('THB 500')
    expect(formatCurrency(1000, 'SGD')).toBe('SGD 1,000')
  })

  it('handles null, undefined, empty, and invalid amounts gracefully', () => {
    expect(formatCurrency(null, 'USD')).toBe('—')
    expect(formatCurrency(undefined, 'USD')).toBe('—')
    expect(formatCurrency('', 'USD')).toBe('—')
    expect(formatCurrency('   ', 'USD')).toBe('—')
    expect(formatCurrency('not-a-number', 'USD')).toBe('—')
    expect(formatCurrency(NaN, 'USD')).toBe('—')
  })

  it('formats zero amounts correctly', () => {
    expect(formatCurrency(0, 'USD')).toBe('$0')
    expect(formatCurrency(0, 'INR')).toBe('₹0')
  })

  it('rounds decimal amounts to the nearest whole integer', () => {
    expect(formatCurrency(49.99, 'USD')).toBe('$50')
    expect(formatCurrency(12.4, 'EUR')).toBe('€12')
    expect(formatCurrency('99.6', 'GBP')).toBe('£100')
  })
})

describe('formatAdmissionFee', () => {
  it('handles free admission', () => {
    expect(formatAdmissionFee({ admission_fee: 0 })).toBe('🆓 Free')
    expect(formatAdmissionFee({ admission_fee_usd: 0 })).toBe('🆓 Free')
    expect(formatAdmissionFee({ admission_fee: 0, admission_fee_currency: 'EUR' })).toBe('🆓 Free')
  })

  it('formats native fee already in the trip currency without conversion parentheses', () => {
    const attrInr = { admission_fee: 50, admission_fee_currency: 'INR' }
    expect(formatAdmissionFee(attrInr, 'INR')).toBe('💰 ₹50')

    const attrEur = { admission_fee: 15, admission_fee_currency: 'EUR' }
    expect(formatAdmissionFee(attrEur, 'EUR')).toBe('💰 €15')

    const attrUsd = { admission_fee: 25, admission_fee_currency: 'USD' }
    expect(formatAdmissionFee(attrUsd, 'USD')).toBe('💰 $25')
  })

  it('formats correctly matched currency conversion (structured conversion object)', () => {
    const attrEur = { admission_fee: 20, admission_fee_currency: 'EUR' }
    const convEurInr = {
      original_currency: 'EUR',
      target_currency: 'INR',
      exchange_rate: 93.5,
    }
    // 20 * 93.5 = 1870
    expect(formatAdmissionFee(attrEur, 'INR', convEurInr)).toBe('💰 ₹1,870 (€20)')
  })

  it('does not apply mismatched conversion pair to an unrelated fee currency', () => {
    const attrEur = { admission_fee: 30, admission_fee_currency: 'EUR' }
    // Conversion is for USD -> INR, not EUR -> INR
    const convUsdInr = {
      original_currency: 'USD',
      target_currency: 'INR',
      exchange_rate: 86.5,
    }
    // Must NOT apply 86.5 to EUR! Must preserve original EUR 30
    expect(formatAdmissionFee(attrEur, 'INR', convUsdInr)).toBe('💰 €30')
  })

  it('preserves the original fee currency when conversion is missing or null', () => {
    const attrGbp = { admission_fee: 45, admission_fee_currency: 'GBP' }
    expect(formatAdmissionFee(attrGbp, 'INR', null)).toBe('💰 £45')
    expect(formatAdmissionFee(attrGbp, 'USD', undefined)).toBe('💰 £45')
  })

  it('formats USD fee converted to another currency', () => {
    const attrUsd = { admission_fee_usd: 20 }
    const convUsdInr = {
      original_currency: 'USD',
      target_currency: 'INR',
      exchange_rate: 86.5,
    }
    // 20 * 86.5 = 1730
    expect(formatAdmissionFee(attrUsd, 'INR', convUsdInr)).toBe('💰 ₹1,730 ($20 USD)')

    const convUsdEur = {
      original_currency: 'USD',
      target_currency: 'EUR',
      exchange_rate: 0.92,
    }
    // 20 * 0.92 = 18.4 -> 18
    expect(formatAdmissionFee(attrUsd, 'EUR', convUsdEur)).toBe('💰 €18 ($20 USD)')
  })

  it('formats USD fee without conversion when target currency is not USD', () => {
    const attrUsd = { admission_fee_usd: 35 }
    expect(formatAdmissionFee(attrUsd, 'INR', null)).toBe('💰 $35 USD')
  })

  it('formats USD fee directly when target currency is USD', () => {
    const attrUsd = { admission_fee_usd: 35 }
    expect(formatAdmissionFee(attrUsd, 'USD')).toBe('💰 $35')
  })

  it('formats unlabelled numeric fee in target currency', () => {
    expect(formatAdmissionFee({ admission_fee: 40 }, 'USD')).toBe('💰 $40')
    expect(formatAdmissionFee({ admission_fee: 100 }, 'INR')).toBe('💰 ₹100')
    expect(formatAdmissionFee({ admission_fee: 15 }, 'EUR')).toBe('💰 €15')
  })

  it('returns null when fee information is missing, null, or invalid', () => {
    expect(formatAdmissionFee(null)).toBeNull()
    expect(formatAdmissionFee(undefined)).toBeNull()
    expect(formatAdmissionFee({})).toBeNull()
    expect(formatAdmissionFee({ name: 'Eiffel Tower' })).toBeNull()
    expect(formatAdmissionFee({ admission_fee: null, admission_fee_usd: null })).toBeNull()
  })

  it('does not produce a false conversion when conversion data is invalid or incomplete', () => {
    const attr = { admission_fee_usd: 25 }

    // Missing exchange_rate
    expect(formatAdmissionFee(attr, 'INR', { original_currency: 'USD', target_currency: 'INR' })).toBe('💰 $25 USD')

    // Non-numeric rate
    expect(formatAdmissionFee(attr, 'INR', { original_currency: 'USD', target_currency: 'INR', exchange_rate: 'invalid' })).toBe('💰 $25 USD')

    // Zero or negative rate
    expect(formatAdmissionFee(attr, 'INR', { original_currency: 'USD', target_currency: 'INR', exchange_rate: 0 })).toBe('💰 $25 USD')
    expect(formatAdmissionFee(attr, 'INR', { original_currency: 'USD', target_currency: 'INR', exchange_rate: -10 })).toBe('💰 $25 USD')

    // Incomplete native fee conversion
    const nativeAttr = { admission_fee: 50, admission_fee_currency: 'JPY' }
    expect(formatAdmissionFee(nativeAttr, 'USD', { original_currency: 'JPY', target_currency: 'USD', exchange_rate: null })).toBe('💰 ¥50')
  })
})

