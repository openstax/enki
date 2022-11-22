import { basename, join, resolve } from 'path';
import * as sourceMapSupport from 'source-map-support';
import { Factory } from './model/factory';
import { Builder, ResourceFile } from './model/file';
import { PageFile } from './model/page';
import { TocFile } from './model/toc';

sourceMapSupport.install()

class Factorio {
    public readonly pages: Factory<PageFile>
    public readonly tocs: Factory<TocFile>
    public readonly resources: Factory<ResourceFile>

    constructor(pageBuilder: Builder<PageFile>, tocBuilder: Builder<TocFile>, resourceBuilder: Builder<ResourceFile>) {
        this.pages = new Factory(pageBuilder, resolve)
        this.tocs = new Factory(tocBuilder, resolve)
        this.resources = new Factory(resourceBuilder, resolve)
    }
}

async function fn() {

    const factorio: Factorio = new Factorio(
        absPath => new PageFile(absPath),
        absPath => new TocFile(absPath),
        absPath => new ResourceFile(absPath),
    )

    // factorio.tocs.getOrAdd('../data/astronomy/_attic/IO_DISASSEMBLE_LINKED/astronomy-2e.toc.xhtml', __filename)
    factorio.tocs.getOrAdd('../test.toc.xhtml', __filename)

    // Load up the models
    for (const tocFile of factorio.tocs.all) {
        await tocFile.parse(factorio.pages, factorio.resources)
    }
    for (const page of factorio.pages.all) {
        await page.parse(factorio.pages, factorio.resources)
    }
    for (const resource of factorio.resources.all) {
        await resource.parse(factorio.pages, factorio.resources)
    }
    const allFiles = [...factorio.tocs.all, ...factorio.pages.all, ...factorio.resources.all]

    // Rename Page files
    Array.from(factorio.pages.all).forEach(p => p.rename(p.newPath.replace(':', '-colon-'), undefined))

    // Rename Resource files by adding a file extension to them
    Array.from(factorio.resources.all).forEach(r => {
        const { mimeType, originalExtension } = r.data
        let newExtension = (ResourceFile.mimetypeExtensions)[mimeType] || originalExtension
        r.rename(`${r.newPath}.${newExtension}`, undefined)
    })


    // Move all the files to a test directory
    for (const f of allFiles) {
        f.rename(`${join(__dirname, '../testing')}/${basename(f.newPath)}`, undefined)
    }
    for (const f of allFiles) {
        await f.write()
    }
    for (const tocFile of factorio.tocs.all) {
        await tocFile.writeOPFFile(`${tocFile.newPath}.opf`)
    }
}

fn().catch(err => console.error(err))