import {
  jest,
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
} from '@jest/globals'
import { readFileSync } from 'fs'
import { MockFileSystem, mockfs } from '../mock-fs'
import { factorio } from './singletons'
import { XmlFile } from '../model/file'
import { TocFile, OpfFile, NcxFile, TocTree, TocTreeType } from './toc'

jest.mock('fs')

async function writeAndCheckSnapshot<T, TBook, TPage, TResource>(
  n: XmlFile<T, TBook, TPage, TResource>,
  destPath: string
) {
  n.rename(destPath, undefined)
  await n.write()
  expect(readFileSync(destPath, 'utf8')).toMatchSnapshot()
}

function simplifyToc(toc: TocTree): unknown {
  return toc.type === TocTreeType.LEAF
    ? {
        type: toc.type,
        tocType: toc.tocType,
        tocTargetType: toc.tocTargetType,
        title: toc.title,
        page: toc.page.readPath,
      }
    : {
        type: toc.type,
        tocType: toc.tocType,
        title: toc.title,
        children: toc.children.map(simplifyToc),
      }
}

describe('TocFile and Friends', () => {
  const tocPath = '/foo/thebook.toc.xhtml'
  const destPath = '/output/thebooktoc.xhtml'
  const metadataPath = '/foo/thebook.toc-metadata.json'
  const collxmlPath = '/IO_FETCHED/collections/bookslug.collection.xml'
  const metadataJSON = {
    title: 'booktitle',
    revised: '2022-12-13',
    slug: 'bookslug',
    license: { url: 'http://licenseurl' },
    language: 'language',
  }

  const collxmlContent =
    '<collection authors="howdy" xmlns="http://cnx.rice.edu/collxml"/>'

  describe('with an empty book', () => {
    const emptyToc = `<html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <nav/>
            </body>
        </html>`

    beforeEach(() => {
      const fs: MockFileSystem = {}
      fs[tocPath] = emptyToc
      fs[metadataPath] = JSON.stringify(metadataJSON)
      fs[collxmlPath] = collxmlContent
      mockfs(fs)
    })
    afterEach(() => {
      mockfs.restore()
    })

    it('parses an empty ToC file', async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      await f.parse(factorio) // just for code coverage reasons to verify we only parse once
      expect(f.parsed.title).toBe(metadataJSON.title)
      await writeAndCheckSnapshot(f, destPath)
    })

    it('generates an OPF file from an empty ToC file', async () => {
      const r = new OpfFile(tocPath)
      await r.parse(factorio)
      expect(r.parsed.title).toBe(metadataJSON.title)
      await writeAndCheckSnapshot(r, destPath)
    })

    it('generates an NCX file from an empty ToC file', async () => {
      const r = new NcxFile(tocPath)
      await r.parse(factorio)
      expect(r.parsed.title).toBe(metadataJSON.title)
      await writeAndCheckSnapshot(r, destPath)
    })
  })

  describe('Cover image with TocFile and Friends', () => {
    const tocPath = '/foo/thebook.toc.xhtml'
    const destPath = '/output/thebooktoc.xhtml'
    const metadataPath = '/foo/thebook.toc-metadata.json'
    const collxmlPath = '/IO_FETCHED/collections/bookslug.collection.xml'
    const coverImagePath = '/IO_FETCHED/cover/bookslug-cover.jpg'
    const metadataJSON = {
      title: 'booktitle',
      revised: '2022-12-13',
      slug: 'bookslug',
      license: { url: 'http://licenseurl' },
      language: 'language',
    }

    const collxmlContent =
      '<collection authors="howdy" xmlns="http://cnx.rice.edu/collxml"/>'

    describe('with an empty book', () => {
      const emptyToc = `<html xmlns="http://www.w3.org/1999/xhtml">
              <body>
                  <nav/>
              </body>
          </html>`

      beforeEach(() => {
        const fs: MockFileSystem = {}
        fs[tocPath] = emptyToc
        fs[metadataPath] = JSON.stringify(metadataJSON)
        fs[collxmlPath] = collxmlContent
        fs[coverImagePath] = 'here should be cover image JPEG data'
        mockfs(fs)
      })
      afterEach(() => {
        mockfs.restore()
      })

      it('parses an empty ToC file', async () => {
        const f = new TocFile(tocPath)
        await f.parse(factorio)
        await f.parse(factorio) // just for code coverage reasons to verify we only parse once
        expect(f.parsed.title).toBe(metadataJSON.title)
        await writeAndCheckSnapshot(f, destPath)
      })

      it('generates an OPF file from an empty ToC file', async () => {
        const r = new OpfFile(tocPath)
        await r.parse(factorio)
        expect(r.parsed.title).toBe(metadataJSON.title)
        await writeAndCheckSnapshot(r, destPath)
      })

      it('generates an NCX file from an empty ToC file', async () => {
        const r = new NcxFile(tocPath)
        await r.parse(factorio)
        expect(r.parsed.title).toBe(metadataJSON.title)
        await writeAndCheckSnapshot(r, destPath)
      })
    })
  })

  describe('with a small book', () => {
    const unitTitle = 'UnitTitle'
    const chapterTitle = 'ChapterTitle'
    const pageTitle = 'PageTitle'
    const pageName = 'iamthepage.xhtml'
    const imageName = 'some-image-name.jpeg'
    const pageNotInTocName = 'anorphanpage.xhtml'
    const smallToc = `<html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <nav>
                    <ol>
                        <li data-toc-type="unit" cnx-archive-shortid="removeme" cnx-archive-uri="removeme" itemprop="removeme">
                            <span>${unitTitle}</span>
                            <ol>
                                <li data-toc-type="chapter" cnx-archive-shortid="removeme" cnx-archive-uri="removeme" itemprop="removeme">
                                    <span>${chapterTitle}</span>
                                    <ol>
                                        <li data-toc-type="page" data-toc-target-type="intro">
                                            <a href="${pageName}"><span>${pageTitle}</span></a>
                                        </li>
                                    </ol>
                                </li>
                            </ol>
                        </li>
                    </ol>
                </nav>
            </body>
        </html>`

    const pageContent = `<html xmlns="http://www.w3.org/1999/xhtml">
        <body>
            <img src="${imageName}" />
            <!-- Has MathML and remote resources -->
            <math xmlns="http://www.w3.org/1998/Math/MathML" />
            <iframe />

            <a href="${pageNotInTocName}" />
        </body>
    </html>`

    const pageNotInTocContent = `<html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        </body>
    </html>`

    const imageMetadata = {
      original_name: 'anything.jpg',
      mime_type: 'image/jpeg',
    }

    beforeEach(() => {
      const fs: MockFileSystem = {}
      fs[tocPath] = smallToc
      fs[`/foo/${pageName}`] = pageContent
      fs[`/foo/${pageNotInTocName}`] = pageNotInTocContent
      fs[`/foo/${imageName}.json`] = JSON.stringify(imageMetadata)
      fs[metadataPath] = JSON.stringify(metadataJSON)
      fs[collxmlPath] = collxmlContent
      fs['/IO_BAKED/downloaded-fonts/hi.ttf'] = 'not-real-TTF-bits'
      mockfs(fs)
    })
    afterEach(() => {
      mockfs.restore()
    })

    it('parses a ToC with one page', async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      expect(f.parsed.title).toBe(metadataJSON.title)
      expect(f.parsed.allPages.size).toBe(2)
      expect(f.parsed.toc.length).toBe(1)
      await writeAndCheckSnapshot(f, destPath)
    })

    it('captures data-toc-type for units, chapters, and pages', async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      expect(f.parsed.toc.map(simplifyToc)).toMatchSnapshot()
    })

    it('marks the first page of a chapter with the doc-chapter ARIA role', async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      const unit = f.parsed.toc[0]
      if (unit.type !== TocTreeType.INNER) throw new Error('Expected a unit')
      const chapter = unit.children[0]
      if (chapter.type !== TocTreeType.INNER) {
        throw new Error('Expected a chapter')
      }
      const leaf = chapter.children[0]
      if (leaf.type !== TocTreeType.LEAF) throw new Error('Expected a page')
      expect(leaf.page.ariaRole).toBe('doc-chapter')
    })

    it('generates an OPF file', async () => {
      const f = new OpfFile(tocPath)
      await f.parse(factorio)
      // Parse all the pages and resources
      for (const page of f.parsed.allPages) {
        await page.parse(factorio)
        for (const f of [...page.parsed.pageLinks, ...page.parsed.resources]) {
          await f.parse(factorio)
        }
      }
      for (const resource of factorio.resources.all) {
        await resource.parse(factorio)
      }

      await writeAndCheckSnapshot(f, destPath)
    })

    it('generates an NCX file', async () => {
      const f = new NcxFile(tocPath)
      await f.parse(factorio)
      // Parse all the pages and resources
      for (const page of f.parsed.allPages) {
        await page.parse(factorio)
        for (const f of [...page.parsed.pageLinks, ...page.parsed.resources]) {
          await f.parse(factorio)
        }
      }

      await writeAndCheckSnapshot(f, destPath)
    })
  })

  describe('ancestor titles for chapter/unit intro pages', () => {
    const unitTitle = 'UnitTitle'
    const chapterTitle = 'ChapterTitle'
    const firstPageTitle = 'FirstPageTitle'
    const firstPageName = 'firstpage.xhtml'
    const secondPageTitle = 'SecondPageTitle'
    const secondPageName = 'secondpage.xhtml'
    const smallToc = `<html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <nav>
                    <ol>
                        <li data-toc-type="unit">
                            <span>${unitTitle}</span>
                            <ol>
                                <li data-toc-type="chapter">
                                    <span>${chapterTitle}</span>
                                    <ol>
                                        <li data-toc-type="page" data-toc-target-type="intro">
                                            <a href="${firstPageName}"><span>${firstPageTitle}</span></a>
                                        </li>
                                        <li data-toc-type="page">
                                            <a href="${secondPageName}"><span>${secondPageTitle}</span></a>
                                        </li>
                                    </ol>
                                </li>
                            </ol>
                        </li>
                    </ol>
                </nav>
            </body>
        </html>`

    const pageContent = `<html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        </body>
    </html>`

    beforeEach(() => {
      const fs: MockFileSystem = {}
      fs[tocPath] = smallToc
      fs[`/foo/${firstPageName}`] = pageContent
      fs[`/foo/${secondPageName}`] = pageContent
      fs[metadataPath] = JSON.stringify(metadataJSON)
      fs[collxmlPath] = collxmlContent
      mockfs(fs)
    })
    afterEach(() => {
      mockfs.restore()
    })

    function getChapterAndPages(toc: TocTree[]) {
      const unit = toc[0]
      if (unit.type !== TocTreeType.INNER) throw new Error('Expected a unit')
      const chapter = unit.children[0]
      if (chapter.type !== TocTreeType.INNER) {
        throw new Error('Expected a chapter')
      }
      const [firstPage, secondPage] = chapter.children
      if (
        firstPage.type !== TocTreeType.LEAF ||
        secondPage.type !== TocTreeType.LEAF
      ) {
        throw new Error('Expected two pages')
      }
      return { unit, chapter, firstPage, secondPage }
    }

    it("gives the chapter's first page the chapter's title (not the unit's) as its ancestorTitle", async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      const { chapter, firstPage } = getChapterAndPages(f.parsed.toc)
      // titlePos wraps a real (circular) DOM node - compare it as a
      // pre-computed boolean rather than handing it to a matcher, so a
      // mismatch can't crash the worker trying to serialize the diff.
      expect(firstPage.page.ancestorTitle?.title).toBe(chapterTitle)
      expect(firstPage.page.ancestorTitle?.pos === chapter.titlePos).toBe(true)
    })

    it("does not give the chapter's other pages an ancestorTitle", async () => {
      const f = new TocFile(tocPath)
      await f.parse(factorio)
      const { secondPage } = getChapterAndPages(f.parsed.toc)
      expect(secondPage.page.ancestorTitle).toBe(null)
    })
  })
})
