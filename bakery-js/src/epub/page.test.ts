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
import { factorio } from './singletons'
import { XmlFile } from '../model/file'
import { PageFile } from './page'
import { parseXml } from '../utils'

jest.mock('fs')

async function writeAndCheckSnapshot<T, TBook, TPage, TResource>(
  n: XmlFile<T, TBook, TPage, TResource>,
  destPath: string
) {
  n.rename(destPath, undefined)
  await n.write()
  expect(readFileSync(destPath, 'utf8')).toMatchSnapshot()
}

describe('Pages', () => {
  const titleText = 'KinematicsInFourDimensions'
  const otherPageFilename = 'pageLink1'

  const minimalPage = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head/>
      <body>
        <h1 data-type="document-title">${titleText}</h1>
      </body>
    </html>`

  const alternateWithAllTheFields = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <body>
        <h2 data-type="document-title">${titleText}</h2>
        <math xmlns="http://www.w3.org/1998/Math/MathML" />
        <iframe/>
        <a href="./${otherPageFilename}"/>
        <a id="this-is-valid-html"/>
      </body>
    </html>`

  const compositePage = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <body>
        <div data-type="composite-page">
          <h3 data-type="title">${titleText}</h3>
        </div>
      </body>
    </html>`

  const untitledPage = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <body>
      </body>
    </html>`

  const pageWithABunchOfSerializerOptions = `
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head/>
      <body>
        <style></style>
        <script></script>
        <h2 data-type="document-title">${titleText}</h2>
        <math>
          <annotation-xml/>
        </math>
        <div itemprop="removeme" valign="removeme" group-by="removeme" use-subtitle="removeme"></div>
        <div class="os-has-iframe os-has-link">
          <iframe class="os-is-iframe" src="https://example"/>
        </div>
        <a href="./${otherPageFilename}"/>
        <a href="./${otherPageFilename}#target-id"/>
        <img src="./notarealimage.jpg"/>
      </body>
    </html>`

  beforeEach(() => {
    process.chdir('/')
    const fs: any = {}
    fs[otherPageFilename] = 'contentsdoesnotmatterjustexistence'
    mockfs(fs)
  })
  afterEach(() => mockfs.restore())

  it('parses an empty page', async () => {
    const p = new PageFile('somepath')
    p.readXml = (_) => Promise.resolve(parseXml(minimalPage))
    await p.parse(factorio)
    expect(p.parsed).toMatchSnapshot()
    expect(p.parsed.hasMathML).toBe(false)
    expect(p.parsed.hasRemoteResources).toBe(false)
    expect(p.parsed.title).toBe(titleText)
  })
  it('parses all the fields with a simple page', async () => {
    const p = new PageFile('somepath')
    p.readXml = (_) => Promise.resolve(parseXml(alternateWithAllTheFields))
    await p.parse(factorio)
    expect(p.parsed).toMatchSnapshot()
    expect(p.parsed.hasMathML).toBe(true)
    expect(p.parsed.hasRemoteResources).toBe(true)
    expect(p.parsed.title).toBe(titleText)
  })

  it('parses a composite page title', async () => {
    const p = new PageFile('somepath')
    p.readXml = (_) => Promise.resolve(parseXml(compositePage))
    await p.parse(factorio)
    expect(p.parsed.title).toBe(titleText)
    expect(p.parsed).toMatchSnapshot()
  })
  it('parses an untitled page and set the title to be "untitled"', async () => {
    const p = new PageFile('somepath')
    p.readXml = (_) => Promise.resolve(parseXml(untitledPage))
    await p.parse(factorio)
    expect(p.parsed.title).toBe('untitled')
  })

  describe('conversions', () => {
    it('converts a simple file', async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(minimalPage))
      await p.parse(factorio)
      await p.write()
      expect(readFileSync(p.newPath, 'utf8')).toMatchSnapshot()
    })

    it('converts a page that exercises a bunch of serializer options', async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) =>
        Promise.resolve(parseXml(pageWithABunchOfSerializerOptions))
      await p.parse(factorio)
      await p.parse(factorio) // Parse a second time for code coverage reasons (to check at we don't actually parse twice)
      await p.write()
      expect(readFileSync(p.newPath, 'utf8')).toMatchSnapshot()
    })

    it('renames relative to a file', async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) =>
        Promise.resolve(parseXml(pageWithABunchOfSerializerOptions))
      await p.parse(factorio)
      p.rename('../newname', '/dir1/dir2/dir3/filename')
      expect(p.newPath).toBe('/dir1/dir2/newname')
    })
  })
})
