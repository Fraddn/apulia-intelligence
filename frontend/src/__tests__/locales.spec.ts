import { describe, expect, it } from 'vitest'
import en from '../locales/en'
import itMessages from '../locales/it'

function keys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix]
  return Object.entries(value).flatMap(([key, child]) => keys(child, prefix ? `${prefix}.${key}` : key))
}

describe('locales', () => {
  it('Italian and English have the same keys', () => {
    expect(keys(itMessages).sort()).toEqual(keys(en).sort())
  })

  it('no translation is empty', () => {
    for (const messages of [en, itMessages]) {
      for (const key of keys(messages)) {
        const value = key.split('.').reduce<unknown>((node, part) => (node as Record<string, unknown>)[part], messages)
        expect(String(value).trim(), key).not.toBe('')
      }
    }
  })

  it('covers every ATECO section and province', () => {
    expect(Object.keys(en.sections)).toEqual('ABCDEFGHIJKLMNOPQRSTU'.split(''))
    expect(Object.keys(en.provinces).sort()).toEqual(['BA', 'BR', 'BT', 'FG', 'LE', 'TA'])
  })
})
