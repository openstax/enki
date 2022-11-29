import { assertValue } from "../utils"
import { dom, Dom } from "../minidom"
import type { Factory } from "./factory"
import { ResourceFile, XMLFile } from "./file"
import type { PageFile } from "./page"
import type { OpfFile } from "./toc"
import { dirname, relative } from "path"

type ContainerData = OpfFile[]

export class ContainerFile extends XMLFile<ContainerData> {
    protected async innerParse(_1: Factory<PageFile>, _2: Factory<ResourceFile>, tocFactory: Factory<OpfFile>): Promise<ContainerData> {
        const doc = dom(await this.readXml(this.readPath))
        return doc.map('//books:book', b => {
            const slug = assertValue(b.attr('slug'))
            return tocFactory.getOrAdd(`../../IO_DISASSEMBLE_LINKED/${slug}.toc.xhtml`, this.readPath)
        })
    }
    protected transform(doc: Dom) {
        const books = this.data.map(t => {
            const p = relative(dirname(this.newPath), t.newPath)
            return doc.create('cont:rootfile', {'media-type': "application/oebps-package+xml", 'full-path': p})
        })
        const newRoot = doc.create('cont:container', { version: "1.0" }, [
            doc.create('cont:rootfiles', {}, books)
        ])
        return newRoot
    }

}