import {describe, expect, it, afterEach, beforeEach} from '@jest/globals'
import { readFileSync } from 'fs'
import mockfs from 'mock-fs'
import { factorio } from './factorio'
import { ResourceFile } from './file'

describe('ResourceFile', () => {
    const resourceHref = '/foo/resources/fakepath'
    const resourcePath = '/foo/IO_RESOURCES/fakepath'
    const metadataPath = '/foo/IO_RESOURCES/fakepath.json'
    const metadataJSON = {
        original_name: 'anything.jpg', 
        mime_type: 'image/jpeg', 
    }
    const resourceContents = 'the contents of the image'

    it('renames the input directory to IO_RESOURCES and parses the JSON meta file to find out the mime type', async () => {
        const r = new ResourceFile(resourceHref)
        r.readJson = <T>(filename: string): T => {
            expect(filename).toBe(metadataPath)
            return metadataJSON as T
        }
        await r.parse(factorio.pages, factorio.resources, factorio.tocs)
        expect(r.data.mimeType).toBe('image/jpeg')
        expect(r.data.originalExtension).toBe('jpg')
    })

    beforeEach(() => {
        const fs: any = {}
        fs[resourcePath] = resourceContents
        fs[metadataPath] = JSON.stringify(metadataJSON)
        fs['/bar/resources/'] = {} // ensure the destination dir exists
        mockfs(fs)
    })

    afterEach(() => {
        mockfs.restore()
    })

    it('copies the resource to the destination directory', async () => {
        const destPath = '/bar/resources/fakepath2'
        const r = new ResourceFile(resourceHref)
        await r.parse(factorio.pages, factorio.resources, factorio.tocs)
        r.rename(destPath, undefined)
        await r.write()
        expect(readFileSync(destPath, 'utf8')).toBe(resourceContents)
    })
})