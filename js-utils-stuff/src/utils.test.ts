import { describe, expect, it, beforeEach, afterEach } from '@jest/globals'
import { readFileSync } from 'fs'
import mockfs from 'mock-fs'
import { parseXml, writeXmlWithSourcemap } from './utils'

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
})
