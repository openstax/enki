import { describe, expect, it, afterEach, jest } from '@jest/globals'
import { mockfs } from './mock-fs'
import {
  writeFileSync,
  readFileSync,
  existsSync,
  rmSync,
  copyFileSync,
  constants,
  mkdirSync,
  readdirSync,
  createWriteStream,
} from 'fs'

jest.mock('fs')

describe('mockfs', () => {
  afterEach(() => {
    mockfs.restore()
  })

  it('can attach, read, write, and restore', async () => {
    mockfs({
      '/': { a: { b: 'test' } },
    })
    expect(readFileSync('/a/b')).toStrictEqual('test')
    writeFileSync('b', Buffer.from('something'))
    expect(() => writeFileSync('/a/b/c', Buffer.from('something'))).toThrow(
      /file/i
    )
    expect(() => writeFileSync('/z/c', '\n')).toThrow(/does not exist/i)
    expect(() => writeFileSync('/a', '\n')).toThrow(/directory/i)
    expect(readFileSync('b', { encoding: 'utf8' })).toStrictEqual('something')

    mockfs.restore()
    mockfs({ b: 'test' })
    expect(() => readFileSync('b')).not.toThrow()
    expect(existsSync('path/that/does/not/exist')).toBe(false)
  })

  it('can mkdirSync', () => {
    mockfs({})
    writeFileSync('a', 'something')
    expect(() => mkdirSync('a/b')).toThrow(/file/i)
    expect(() => mkdirSync('x/y/z/w')).toThrow(/exist/i)
    expect(() => mkdirSync('x/y/z/w', { recursive: true })).not.toThrow()
    expect(existsSync('x/y/z/w')).toBe(true)
    expect(() => mkdirSync('x/y/z/w/u/v', { recursive: true })).not.toThrow()
  })

  it('can rmSync', () => {
    mockfs({
      '/a/b/c': 'test',
    })
    expect(existsSync('/a/b/c')).toBe(true)
    expect(() => rmSync('/a/b')).toThrow(/directory/i)
    expect(() => rmSync('/a/b/c')).not.toThrow()
    expect(existsSync('/a/b/c')).toBe(false)
    expect(existsSync('/a/b')).toBe(true)
    expect(() => rmSync('/a/b')).toThrow(/directory/i)
    expect(() => rmSync('/a/b', { recursive: true })).not.toThrow()
    expect(existsSync('/a/b')).toBe(false)
    expect(existsSync('/c')).toBe(false)
    expect(() => rmSync('/c')).toThrow(/does not exist/i)
  })

  it('can copyFileSync', () => {
    mockfs({
      'a/b/c': 'file content',
    })
    expect(existsSync('a/b/d')).toBe(false)
    copyFileSync('a/b/c', 'a/b/d')
    expect(readFileSync('a/b/d')).toStrictEqual('file content')
    expect(() =>
      copyFileSync('a/b/c', 'a/b/d', constants.COPYFILE_EXCL)
    ).toThrow(/exists/i)
    expect(() => copyFileSync('a/b/c', 'a/b/d')).not.toThrow()
  })

  it('can readdirSync', () => {
    mockfs({
      a: {
        b: '',
        c: '',
        d: '',
        e: {},
      },
    })
    expect(readdirSync('a')).toStrictEqual(['b', 'c', 'd', 'e'])
    expect(() => readdirSync('b')).toThrow(/exist/i)
    expect(() => readdirSync('a', { withFileTypes: true })).toThrow(/options/i)
  })

  it('can createWriteStream', () => {
    mockfs({})
    const writer = createWriteStream('a', { encoding: 'utf8' })
    writer.write('stuff')
    writer.end()
    writer.close()
    expect(existsSync('a')).toBe(true)
    expect(readFileSync('a')).toStrictEqual('stuff')
    const writer2 = createWriteStream('b', 'utf-8')
    writer2.write('test')
    writer2.end()
    writer2.close()
    expect(readFileSync('b')).toStrictEqual('test')
    const writer3 = createWriteStream('c')
    const callback = jest.fn()
    writer3.write('1'.repeat(1 << 20))
    writer3.end()
    writer3.close(callback)
    expect(readFileSync('c')).toHaveLength(1 << 20)
    expect(callback).toHaveBeenCalledTimes(1)
  })
})
