import {
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
  jest,
} from '@jest/globals'
import { Factory } from './factory'

describe('Factory', () => {
  const builder = (s: string) => s
  const canonicalizer = (s: string) => s.toUpperCase()
  it('can clear', () => {
    const f = new Factory(builder, canonicalizer)
    expect(f.get('somenonexistentpath', undefined)).toBe(undefined)
    expect(f.size).toBe(0)

    expect(f.getOrAdd('somepath', undefined)).toBe('SOMEPATH')
    expect(f.size).toBe(1)
    expect([...f.all]).toEqual(['SOMEPATH'])

    f.clear()
    expect(f.size).toBe(0)

    expect(f.getOrAdd('somepath', undefined)).toBe('SOMEPATH')
    expect(f.size).toBe(1)

    expect(f.get('afile', '/nonexistentdir')).toBe(undefined)

    f.remove('somepath')
    expect(f.size).toBe(0)
  })
})
