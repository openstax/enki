import { assertValue } from "../utils"
import { dom } from "../minidom"
import { XmlFile } from "./file"
import type { OpfFile } from "./toc"
import { dirname, join, relative } from "path"
import type { Factorio } from "./factorio"

type ContainerData = OpfFile[]

export class ContainerFile extends XmlFile<ContainerData> {
    public async parse(factorio: Factorio): Promise<void> {
        if (this._parsed !== undefined) return // Only parse once
        const doc = dom(await this.readXml(this.readPath))
        this._parsed = doc.map('//books:book', b => {
            const slug = assertValue(b.attr('slug'))
            return factorio.opfs.getOrAdd(`../../IO_DISASSEMBLE_LINKED/${slug}.toc.xhtml`, this.readPath)
        })
    }
    protected async convert(): Promise<Node> {
        const doc = dom(await this.readXml(this.readPath))
        const books = this.parsed.map(t => {
            // full-path entries are not relative. They're from the root of the EPUB.
            const epubRoot = join(dirname(this.newPath), '..')
            const p = relative(epubRoot, t.newPath)
            return doc.create('cont:rootfile', {'media-type': "application/oebps-package+xml", 'full-path': p})
        })
        const newRoot = doc.create('cont:container', { version: "1.0" }, [
            doc.create('cont:rootfiles', {}, books)
        ])
        return newRoot.node
    }
}
