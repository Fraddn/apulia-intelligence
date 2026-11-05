const LOCALE_TAGS: Record<string, string> = { it: 'it-IT', en: 'en-GB' }

export function formatNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(LOCALE_TAGS[locale] ?? locale).format(value)
}

export function formatPercent(part: number, total: number, locale: string): string {
  if (!total) return '–'
  return new Intl.NumberFormat(LOCALE_TAGS[locale] ?? locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(part / total)
}

export function formatDate(value: string | null, locale: string): string {
  if (!value) return '–'
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Intl.DateTimeFormat(LOCALE_TAGS[locale] ?? locale, { dateStyle: 'medium' }).format(
    new Date(year, month - 1, day),
  )
}

export function formatCurrency(value: number | null, locale: string, compact = false): string {
  if (value === null || value === undefined) return '–'
  return new Intl.NumberFormat(LOCALE_TAGS[locale] ?? locale, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact ? 'compact' : 'standard',
  }).format(value)
}
