import { describe, expect, it } from 'vitest'
import { DIVISIONS, divisionsFor } from '../ateco'
import en from '../locales/en'

describe('ateco divisions', () => {
  it('lists the divisions of a section', () => {
    expect(divisionsFor('J')).toEqual(['58', '59', '60', '61', '62', '63'])
    expect(divisionsFor('C')[0]).toBe('10')
    expect(divisionsFor('C').at(-1)).toBe('33')
    expect(divisionsFor('D')).toEqual(['35'])
    expect(divisionsFor('')).toEqual([])
    expect(divisionsFor('Z')).toEqual([])
  })

  it('has the 88 ATECO 2007 divisions, all translated', () => {
    expect(DIVISIONS).toHaveLength(88)
    expect(Object.keys(en.divisions).sort()).toEqual([...DIVISIONS].sort())
  })
})
