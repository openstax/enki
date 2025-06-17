import {
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
  jest,
} from '@jest/globals'
import { readFileSync } from 'fs'
import { mockfs } from '../mock-fs'
import { factorio } from '../epub/singletons'
import { ResourceFile } from './file'

jest.mock('fs')

describe('ResourceFile', () => {
  const resourceHref = '/foo/resources/fakepath'
  const resourcePath = '/foo/IO_RESOURCES/fakepath'
  const metadataPath = '/foo/IO_RESOURCES/fakepath.json'
  const metadataJSON = {
    original_name: 'anything.jpg',
    mime_type: 'image/jpeg',
  }
  const resourceContents = 'the contents of the image'
  const destPath = '/bar/resources/fakepath2'

  it('renames the input directory to IO_RESOURCES and parses the JSON meta file to find out the mime type', async () => {
    const r = new ResourceFile(resourceHref)
    // Replace the read method with a mock
    const s = jest.spyOn(r, 'readJson')
    s.mockReturnValue(metadataJSON)

    await r.parse(factorio)
    expect(r.parsed.mimeType).toBe('image/jpeg')
    expect(r.parsed.originalExtension).toBe('jpg')
  })

  beforeEach(() => {
    const fs: any = {}
    fs[resourcePath] = resourceContents
    fs[metadataPath] = JSON.stringify(metadataJSON)
    mockfs(fs)
  })

  afterEach(() => {
    mockfs.restore()
  })

  it('copies the resource to the destination directory', async () => {
    const r = new ResourceFile(resourceHref)
    await r.parse(factorio)
    r.rename(destPath, undefined)
    await r.write()
    expect(readFileSync(destPath, 'utf8')).toBe(resourceContents)
  })
})
