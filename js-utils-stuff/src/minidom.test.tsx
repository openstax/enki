import { describe, expect, it, beforeEach } from '@jest/globals'
import { Dom, dom, fromJSX } from './minidom'
import { parseXml } from './utils'

describe('minidom', () => {
  describe('with a simple document', () => {
    let doc = undefined as unknown as Document
    let $doc = undefined as unknown as Dom
    let $root = undefined as unknown as Dom

    beforeEach(() => {
      doc = parseXml(
        '<root><child id="kid1">hello</child><child>world</child></root>'
      )
      $doc = dom(doc)
      $root = dom(doc.documentElement)
    })

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
      const $newKid = $child.replaceWith(<dc:identifier id="newKid" />)
      expect($newKid.tagName).toBe('identifier')
      expect($root.find('*[@id="kid1"]').length).toBe(0)
      $newKid.replaceWith($child)
      expect($root.find('*[@id="kid1"]').length).toBe(1)
      $child.remove()
      expect($root.find('*[@id="kid1"]').length).toBe(0)
    })
    it('gets/sets/removes attributes', () => {
      const theAttrs = { id: 'foo', class: 'bar baz' }
      const newId = 'howdy'
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
    it('combines text from multiple nodes', () => {
      expect($root.text()).toBe('helloworld')
    })
    it('works with has, map, and forEach', () => {
      expect($root.has('child')).toBe(true)
      expect($root.map('*', (n) => n.tagName)).toEqual(['child', 'child'])
      const ret: string[] = []
      $root.forEach('*', (n) => ret.push(n.tagName))
      expect(ret).toEqual(['child', 'child'])
    })
    it('supports getting/replacing children', () => {
      const $child = $root.find('*')[0]
      expect($root.children.length).toBe(2)
      expect($child.node === $root.children[0].node).toBe(true)
      expect(
        $root.children.map((c) => (c as unknown as Element).tagName)
      ).toEqual(['child', 'child'])
      $root.children = []
      expect($root.children).toEqual([])
      $root.children = [$child]
      expect($root.children.length).toBe(1)

      $root.children = []
      expect($root.children.length).toBe(0)
      $root.children = [
        <h:title>
          unimportant title with a <h:title>subtitle</h:title> to boot!
        </h:title>,
      ]
      expect($root.children.length).toBe(1)
    })
    it('supports setting string children', () => {
      $root.children = []
      $root.children = ['howdy']
      expect($root.children.length).toBe(1)
      expect($root.text()).toBe('howdy')
    })
    it('supports creating new elements', () => {
      const $child = $root.find('*')[0]
      const pos = {
        source: { fileName: 'foo.txt', content: null },
        lineNumber: 1,
        columnNumber: 1,
      }
      const $el = $root.create('yeehaw', {}, [$child], pos)
      expect($el.tagName).toBe('yeehaw')
    })
  })
  it('supports creating a Document from just JSX', () => {
    const zero = fromJSX(<h:title />)
    const one = fromJSX(<h:title>singlechild</h:title>)
    const many = fromJSX(
      <h:title>
        many <h:title /> children
      </h:title>
    )
    expect(zero.children).toEqual([])
    expect(one.children.length).toBe(1)
    expect(many.children.length).toBe(3)
  })
})
