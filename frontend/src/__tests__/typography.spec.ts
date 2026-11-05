import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const MIN_FONT_SIZE = 14
const css = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf8')

describe('typography', () => {
  it(`never uses a font size below ${MIN_FONT_SIZE}px`, () => {
    const sizes = [...css.matchAll(/font-size:\s*([^;]+);/g)].map((match) => match[1].trim())
    expect(sizes.length).toBeGreaterThan(0)
    for (const size of sizes) {
      expect(size, `font-size: ${size}`).toMatch(/^\d+px$/)
      expect(parseInt(size, 10), `font-size: ${size}`).toBeGreaterThanOrEqual(MIN_FONT_SIZE)
    }
  })
})
