import {describe, expect, it} from '@jest/globals'
import { dom } from './minidom'
import { parseXml } from './utils'

describe('minidom', () => {
    const doc = parseXml('<root><child id="kid1">hello</child><child>world</child></root>')
    const $doc = dom(doc)
    const $root = dom(doc.documentElement)
    it('returns the tag name of an element', () => {
        expect($root.tagName).toBe('root')
    })
    it('provides access to the underlying DOM node', () => {
        expect($doc.doc).toBe(doc)
        expect($doc.node).toBe(doc)
        expect($root.doc).toBe(doc)
        expect($root.node).toBe(doc.documentElement)
    })
    it('can find nodes via xpath', () => {
        expect($root.find('child').length).toBe(2)
        expect($root.findOne('*[@id="kid1"]')).not.toBe(undefined)
    })
    it('can remove/replace nodes', () => {
        const $child = $root.findOne('*[@id="kid1"]')
        const $newKid = $child.replaceWith(<dc:identifier id="newKid"/>)
        expect($newKid.tagName).toBe('identifier')
        expect($root.find('*[@id="kid1"]').length).toBe(0)
        $newKid.replaceWith($child)
        expect($root.find('*[@id="kid1"]').length).toBe(1)
        $child.remove()
        expect($root.find('*[@id="kid1"]').length).toBe(0)
    })
    it('gets/sets/removes attributes', () => {
        const theAttrs = { id: 'foo', class: 'bar baz' }
        const newId = "howdy"
        // get/set/remove attrs
        expect($root.attrs).toEqual({})
        $root.attrs = theAttrs
        expect($root.attrs).toEqual(theAttrs)
        $root.attrs = {}
        expect($root.attrs).toEqual({})
        // get/set/remove attr
        expect($root.attr('id')).toBe(null)
        $root.attr('id', newId)
        expect($root.attr('id')).toBe(newId)
        $root.attr('id', null)
        $root.attr('somethingthatneverexisted', null)
        expect($root.attrs).toEqual({})
    })
})