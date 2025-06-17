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

  it('writes comments', async () => {
    const doc = parseXml(`<root><!-- I am a comment --></root>`)
    await writeAndCheckSnapshot(doc)
  })
})
