import {
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
  jest,
} from '@jest/globals'
import { readFileSync } from 'fs'
import mockfs from 'mock-fs'
import { factorio } from './singletons'
import { XmlFile } from '../model/file'
import { TocFile } from './toc'

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
      const r = new TocFile(tocPath)
      await r.parse(factorio)
      expect(r.parsed.title).toBe(metadataJSON.title)
      await writeAndCheckSnapshot(r, destPath)
    })
  })

  describe('with a small book', () => {
    const chapterTitle = 'ChapterTitle'
    const pageTitle = 'PageTitle'
    const pageName = 'iamthepage.xhtml'
    const smallToc = `<html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <nav>
                    <ol>
                        <li>
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
            
        </body>
    </html>`

    beforeEach(() => {
      const fs: any = {}
      fs[tocPath] = smallToc
      fs[`/foo/${pageName}`] = pageContent
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
      expect(f.parsed.allPages.size).toBe(1)
      expect(f.parsed.toc.length).toBe(1)
      await writeAndCheckSnapshot(f, destPath)
    })
  })
})
