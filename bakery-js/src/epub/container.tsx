import { assertValue } from '../utils'
import { dom, fromJSX } from '../minidom'
import { ResourceFile, XmlFile } from '../model/file'
import type { OpfFile } from './toc'
import { dirname, join, relative } from 'path'
import type { Factorio } from '../model/factorio'
import { DIRNAMES } from '../env'
import { PageFile } from './page'

type ContainerData = OpfFile[]

export class ContainerFile extends XmlFile<
  ContainerData,
  OpfFile,
  PageFile,
  ResourceFile
> {
  public async parse(
    factorio: Factorio<OpfFile, PageFile, ResourceFile>
  ): Promise<void> {
    if (this._parsed !== undefined) return // Only parse once
    const doc = dom(await this.readXml(this.readPath))
    this._parsed = doc.map('//books:book', (b) => {
      const slug = assertValue(b.attr('slug'))
      return factorio.books.getOrAdd(
        `../../${DIRNAMES.IO_DISASSEMBLE_LINKED}/${slug}.toc.xhtml`,
        this.readPath
      )
    })
  }
  protected async convert(): Promise<Node> {
    const books = this.parsed.map((t) => {
      // full-path entries are not relative. They're from the root of the EPUB.
      const epubRoot = join(dirname(this.newPath), '..')
      const p = relative(epubRoot, t.newPath)
      return (
        <cont:rootfile
          media-type="application/oebps-package+xml"
          full-path={p}
        />
      )
    })

    return fromJSX(
      <cont:container version="1.0">
        <cont:rootfiles>{books}</cont:rootfiles>
      </cont:container>
    ).node
  }
}
