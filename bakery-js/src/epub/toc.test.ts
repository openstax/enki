import {
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
} from '@jest/globals'
import { readFileSync } from 'fs'
import mockfs from 'mock-fs'
import { factorio } from './singletons'
import { XmlFile } from '../model/file'
import { TocFile, OpfFile, NcxFile } from './toc'

async function writeAndCheckSnapshot<T, TBook, TPage, TResource>(
  n: XmlFile<T, TBook, TPage, TResource>,
  destPath: string
) {
  n.rename(destPath, undefined)
  await n.write()
  expect(readFileSync(destPath, 'utf8')).toMatchSnapshot()
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
      const fs: any = {}
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

  describe('with a small book', () => {
    const chapterTitle = 'ChapterTitle'
    const pageTitle = 'PageTitle'
    const pageName = 'iamthepage.xhtml'
    const imageName = 'some-image-name.jpeg'
    const pageNotInTocName = 'anorphanpage.xhtml'
    const smallToc = `<html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <nav>
                    <ol>
                        <li cnx-archive-shortid="removeme" cnx-archive-uri="removeme" itemprop="removeme">
                            <a href="#chapunused"><span>${chapterTitle}</span></a>
                            <ol>
                                <li>
                                    <a href="${pageName}"><span>${pageTitle}</span></a>
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
      const fs: any = {}
      fs[tocPath] = smallToc
      fs[`/foo/${pageName}`] = pageContent
      fs[`/foo/${pageNotInTocName}`] = pageNotInTocContent
      fs[`/foo/${imageName}.json`] = JSON.stringify(imageMetadata)
      fs[metadataPath] = JSON.stringify(metadataJSON)
      fs[collxmlPath] = collxmlContent
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
})
