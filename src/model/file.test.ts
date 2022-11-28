import {describe, expect, it} from '@jest/globals'
import { factorio } from './factorio'
import { ResourceFile } from './file'

describe('ResourceFile', () => {
    it('renames the input directory to IO_RESOURCES and parses the JSON meta file to find out the mime type', async () => {
        const resourcePath = '/foo/resources/fakepath'
        const metadataPath = '/foo/IO_RESOURCES/fakepath.json'
        const metadataJSON = {
            original_name: 'anything.jpg', 
            mime_type: 'image/jpeg', 
        }
        const r = new ResourceFile(resourcePath)
        r.readJson = <T>(filename: string): T => {
            expect(filename).toBe(metadataPath)
            return metadataJSON as T
        }
        await r.parse(factorio.pages, factorio.resources, factorio.tocs)
        expect(r.data.mimeType).toBe('image/jpeg')
        expect(r.data.originalExtension).toBe('jpg')
    })
})