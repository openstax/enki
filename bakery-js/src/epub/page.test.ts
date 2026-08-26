import {
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
  jest,
} from '@jest/globals'
import { readFileSync } from 'fs'
import { MockFileSystem, mockfs } from '../mock-fs'
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
    const fs: MockFileSystem = {}
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

  describe('heading levels', () => {
    const somePos = {
      source: { fileName: 'somefile.cnxml', content: null },
      lineNumber: 1,
      columnNumber: 1,
    }

    it('promotes the page title to h1 and demotes sibling headings to match, without ever creating a second h1', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h2 data-type="document-title">${titleText}</h2>
              <h2 data-type="title">Level2</h2>
              <h3 data-type="title">SectionOne</h3>
              <h2 data-type="title">Something</h2>
              <h3 data-type="title">SectionTwo</h3>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')
      expect(output).toContain(
        `<h1 data-type="document-title">${titleText}</h1>`
      )
      // "Level2" and "Something" reset to the title's own original depth,
      // but the title is never popped off - so they become h2 siblings
      // under it (not second/third h1s), and "SectionOne"/"SectionTwo"
      // stay nested one level under whichever of the two precedes them.
      expect(output).toMatch(/<h2[^>]*>Level2<\/h2>/)
      expect(output).toMatch(/<h2[^>]*>Something<\/h2>/)
      expect(output).toMatch(/<h3[^>]*>SectionOne<\/h3>/)
      expect(output).toMatch(/<h3[^>]*>SectionTwo<\/h3>/)
      expect(output.match(/<h1[ >]/g)?.length).toBe(1)
      expect(output.match(/<h2[ >]/g)?.length).toBe(2)
      expect(output.match(/<h3[ >]/g)?.length).toBe(2)
    })

    it('clamps a heading that jumps more than one level deeper', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h2 data-type="document-title">${titleText}</h2>
              <h5 data-type="title">TooDeep</h5>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')
      expect(output).toContain(
        `<h1 data-type="document-title">${titleText}</h1>`
      )
      expect(output).toMatch(/<h2[^>]*>TooDeep<\/h2>/)
    })

    it('does not touch a heading that only descends by exactly one level', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h1 data-type="document-title">${titleText}</h1>
              <h2 data-type="title">SectionOne</h2>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')
      expect(output).toContain(
        `<h1 data-type="document-title">${titleText}</h1>`
      )
      expect(output).toMatch(/<h2[^>]*>SectionOne<\/h2>/)
    })

    it("inserts a chapter/unit's ancestorTitle as a leading h1 into the page div, ahead of any pre-existing heading", async () => {
      const chapterTitle = 'Observing the Sky: The Birth of Astronomy'
      // "Chapter Outline" is a nav widget that (in real content) shows up
      // before the page's own title in document order.
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h2 class="os-title">Chapter Outline</h2>
              <h2 data-type="document-title">${titleText}</h2>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      p.ancestorTitle = { title: chapterTitle, pos: somePos }
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(output).toContain(
        `<h1 data-type="document-title">${chapterTitle}</h1>`
      )
      // Only one h1 on the page - the inserted ancestor title, not the
      // page's own title and not the outline widget.
      expect(output.match(/<h1[ >]/g)?.length).toBe(1)

      // The inserted h1 must land inside div[data-type="page"], as its
      // first child - not as a sibling of that div under <body>.
      expect(output).toMatch(
        new RegExp(
          `<div data-type="page">\\s*<h1 data-type="document-title">${chapterTitle}</h1>`
        )
      )

      // Search from <body> onward - <head><title> also contains titleText,
      // and it always precedes the body regardless of heading order.
      const bodyIndex = output.indexOf('<body')
      const h1Index = output.indexOf('<h1', bodyIndex)
      const outlineIndex = output.indexOf('Chapter Outline', bodyIndex)
      const titleIndex = output.indexOf(titleText, bodyIndex)
      expect(h1Index).toBeGreaterThanOrEqual(0)
      expect(h1Index).toBeLessThan(outlineIndex)
      expect(h1Index).toBeLessThan(titleIndex)

      // Both the outline widget and the page's own title become h2
      // siblings of each other, under the real ancestor h1 - neither one
      // is falsely nested under the other.
      expect(output).toMatch(/<h2[^>]*>Chapter Outline<\/h2>/)
      expect(output).toMatch(new RegExp(`<h2[^>]*>${titleText}</h2>`))
    })

    it('does not insert anything when ancestorTitle is unset', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h1 data-type="document-title">${titleText}</h1>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')
      expect(output.match(/<h1[ >]/g)?.length).toBe(1)
      expect(output).toContain(
        `<h1 data-type="document-title">${titleText}</h1>`
      )
    })
  })

  describe('wrapping titled elements', () => {
    it('splits a note with a title into a header and a section, and marks it as having a title', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h1 data-type="document-title">${titleText}</h1>
              <div data-type="note" data-label="Note">
                <h3 data-type="title">Some Note</h3>
                <p>Note body text</p>
              </div>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(output).toContain('class="ui-has-child-title"')
      expect(output).toContain(
        '<header><h2 data-type="title" data-label-parent="Note">Some Note</h2></header>'
      )
      expect(output).toMatch(/<section>\s*<p>Note body text<\/p>\s*<\/section>/)
    })

    it('wraps a titleless example in an empty header and a section containing its body', async () => {
      const page = `
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head/>
          <body>
            <div data-type="page">
              <h1 data-type="document-title">${titleText}</h1>
              <div data-type="example">
                <p>Example body text</p>
              </div>
            </div>
          </body>
        </html>`
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(page))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(output).not.toContain('ui-has-child-title')
      expect(output).toContain('<div data-type="example"><header/><section>')
      expect(output).toMatch(/<p>Example body text<\/p>\s*<\/section>/)
    })
  })

  describe('structural roles', () => {
    const pageWithOwnDiv = `
      <html xmlns="http://www.w3.org/1999/xhtml">
        <head/>
        <body>
          <div data-type="page">
            <h1 data-type="document-title">${titleText}</h1>
          </div>
        </body>
      </html>`

    function pageDivTag(output: string) {
      return output.match(/<div data-type="page"[^>]*>/)?.[0] ?? ''
    }
    function bodyTag(output: string) {
      return output.match(/<body[^>]*>/)?.[0] ?? ''
    }

    it('adds role, epub:type, and aria-label to the page div - not the body - when ariaSpec is set', async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(pageWithOwnDiv))
      p.ariaSpec = {
        role: 'doc-chapter',
        label: 'Observing the Sky: The Birth of Astronomy',
      }
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(pageDivTag(output)).toContain('role="doc-chapter"')
      expect(pageDivTag(output)).toContain('epub:type="chapter"')
      expect(pageDivTag(output)).toContain(
        'aria-label="Observing the Sky: The Birth of Astronomy"'
      )
      // Not on <body> - it does nothing there.
      expect(bodyTag(output)).not.toContain('role=')
    })

    it("falls back to the page's own title as the aria-label when ariaSpec.label is null", async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(pageWithOwnDiv))
      p.ariaSpec = { role: 'doc-preface', label: null }
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(pageDivTag(output)).toContain('epub:type="preface"')
      expect(pageDivTag(output)).toContain(`aria-label="${titleText}"`)
    })

    it('does not add role, epub:type, or aria-label when ariaSpec is unset', async () => {
      const p = new PageFile('somepath')
      p.readXml = (_) => Promise.resolve(parseXml(pageWithOwnDiv))
      await p.parse(factorio)
      await p.write()
      const output = readFileSync(p.newPath, 'utf8')

      expect(pageDivTag(output)).not.toContain('role=')
      expect(pageDivTag(output)).not.toContain('epub:type=')
      expect(pageDivTag(output)).not.toContain('aria-label=')
      expect(bodyTag(output)).not.toContain('role=')
    })
  })
})
