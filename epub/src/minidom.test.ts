import {describe, expect, it} from '@jest/globals'
import { dom } from './minidom'
import { parseXml } from './utils'

describe('minidom', () => {
    const doc = parseXml('<root><child/></root>')
    it('returns the tag name of an element', () => {
        expect(dom(doc.documentElement).tagName).toBe('root')
    })
})