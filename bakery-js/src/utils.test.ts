import {
  describe,
  expect,
  it,
  beforeEach,
  afterEach,
  jest,
} from '@jest/globals'
import { readFileSync } from 'fs'
import { mockfs } from './mock-fs'
import { parseXml, writeXmlWithSourcemap } from './utils'

jest.mock('fs')

async function writeAndCheckSnapshot<T>(n: Node) {
  const destPath = 'out.xml'
  await writeXmlWithSourcemap(destPath, n)
  expect(readFileSync(destPath, 'utf8')).toMatchSnapshot()
}

describe('xml serializing', () => {
  beforeEach(() => {
    mockfs({})
  })
  afterEach(() => {
    mockfs.restore()
  })

  it('writes namespace declarations only once when a prefix is defined on an attribute', async () => {
    const doc = parseXml(`<root>
            <child xmlns:foo="bar" foo:attr="value"/>
        </root>`)
    await writeAndCheckSnapshot(doc)
  })

  it('writes namespace declarations only once when a prefix is defined on an attribute even when there are multiple attributes', async () => {
    const doc =
      parseXml(`<root xmlns:ns2="http://katalysteducation.org/cxlxt/1.0">
      <span ns2:index="name" ns2:name="Wearing, Clive" ns2:born="1938" />
  </root>`)
    await writeAndCheckSnapshot(doc)
  })

  it('does not redeclare an element namespace prefix already bound by an ancestor', async () => {
    const doc = parseXml(
      `<m:math xmlns:m="http://www.w3.org/1998/Math/MathML">
            <m:mrow>
                <m:mn>1</m:mn>
                <m:mo>+</m:mo>
                <m:mn>2</m:mn>
            </m:mrow>
        </m:math>`
    )
    await writeAndCheckSnapshot(doc)
  })

  it('redeclares an element namespace prefix when it is bound to a different namespace in a nested scope', async () => {
    const doc = parseXml(
      `<a:root xmlns:a="urn:one">
            <a:child xmlns:a="urn:two"><a:grandchild/></a:child>
        </a:root>`
    )
    await writeAndCheckSnapshot(doc)
  })

  it('still writes a locally-shadowed prefix declaration even when a same-prefixed attribute is also present', async () => {
    const doc = parseXml(
      `<a:root xmlns:a="urn:one">
            <a:child xmlns:a="urn:two" a:foo="bar"/>
        </a:root>`
    )
    await writeAndCheckSnapshot(doc)
  })

  it('does not redeclare a namespace prefix that was only declared via an ancestor xmlns attribute', async () => {
    const doc = parseXml(
      `<root xmlns:dc="http://purl.org/dc/elements/1.1/">
            <metadata>
                <dc:title>A</dc:title>
                <dc:creator>B</dc:creator>
            </metadata>
        </root>`
    )
    await writeAndCheckSnapshot(doc)
  })

  it('does not duplicate xmlns:prefix when a programmatically-created element uses the same prefix on itself and on an attribute', async () => {
    // Elements built via the DOM API (as minidom/fromJSX does, rather than
    // parsed from XML text) get a resolved prefix/namespaceURI without ever
    // getting a literal `xmlns:prefix` attribute anywhere in the tree.
    const doc = parseXml(`<root/>`)
    const el = doc.createElementNS('http://purl.org/dc/elements/1.1/', 'dc:el')
    el.setAttributeNS('http://purl.org/dc/elements/1.1/', 'dc:foo', 'value')
    doc.documentElement.appendChild(el)
    await writeAndCheckSnapshot(doc)
  })

  it('handles more than one namespace prefix on the same element independently', async () => {
    // `dc` is the element's own tag prefix (programmatically created, so no
    // literal xmlns:dc attribute exists). `opf` is a second, unrelated
    // prefix declared only via an attribute. An attribute using each prefix
    // is also present, to confirm neither prefix's bookkeeping leaks into
    // the other's.
    const doc = parseXml(`<root/>`)
    const el = doc.createElementNS('http://purl.org/dc/elements/1.1/', 'dc:el')
    el.setAttributeNS('http://www.w3.org/2000/xmlns/', 'xmlns:opf', 'urn:opf')
    el.setAttributeNS('urn:opf', 'opf:meta', 'x')
    el.setAttributeNS('http://purl.org/dc/elements/1.1/', 'dc:foo', 'y')
    doc.documentElement.appendChild(el)
    await writeAndCheckSnapshot(doc)
  })

  it('writes comments', async () => {
    const doc = parseXml(`<root><!-- I am a comment --></root>`)
    await writeAndCheckSnapshot(doc)
  })
})
