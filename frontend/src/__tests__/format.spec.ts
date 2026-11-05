import { describe, expect, it } from 'vitest'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '../format'

describe('format', () => {
  it('formats numbers per locale', () => {
    expect(formatNumber(42485, 'it')).toBe('42.485')
    expect(formatNumber(42485, 'en')).toBe('42,485')
  })

  it('formats percentages and handles a zero total', () => {
    expect(formatPercent(41951, 42485, 'en')).toBe('98.7%')
    expect(formatPercent(1, 0, 'en')).toBe('–')
  })

  it('formats dates without timezone shifts', () => {
    expect(formatDate('2026-06-30', 'en')).toBe('30 Jun 2026')
    expect(formatDate('2026-06-30', 'it')).toBe('30 giu 2026')
    expect(formatDate(null, 'it')).toBe('–')
  })

  it('formats euro amounts, full and compact', () => {
    expect(formatCurrency(100000, 'en')).toBe('€100,000')
    expect(formatCurrency(12345.6, 'it')).toMatch(/^12\.346\s€$/)
    expect(formatCurrency(5522713357.69, 'en', true)).toBe('€5.5bn')
    expect(formatCurrency(5522713357.69, 'it', true)).toMatch(/^5,5\sMld\s€$/)
    expect(formatCurrency(null, 'en')).toBe('–')
  })
})
