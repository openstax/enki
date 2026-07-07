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

  it('writes comments', async () => {
    const doc = parseXml(`<root><!-- I am a comment --></root>`)
    await writeAndCheckSnapshot(doc)
  })
})
