import { resolve } from 'path';
import * as sourceMapSupport from 'source-map-support';
import { Factory } from './model/factory';
import { Builder, ResourceFile } from './model/file';
import { PageFile } from './model/page';
import { TocTreeType, TocFile } from './model/toc';

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

    // const toc = factorio.tocs.getOrAdd('../data/astronomy/_attic/IO_DISASSEMBLE_LINKED/astronomy-2e.toc.xhtml', __filename)
    const toc = factorio.tocs.getOrAdd('../test.toc.xhtml', __filename)
    await toc.parse(factorio.pages, factorio.resources)
    const tocInfo = toc.data.toc
    console.log(tocInfo)

    const first = tocInfo[0]
    if (first.type === TocTreeType.LEAF) {
        await first.page.parse(factorio.pages, factorio.resources)
        const pageInfo = first.page.data
        console.log(pageInfo)
        // {
        //   hasMathML: true,
        //   hasRemoteResources: true,
        //   hasScripts: true,
        //   resources: [
        //     ResourceFile {
        //       absPath: '/home/...path-to.../enki/resources/foo.jpg'
        //     }
        //   ]
        // }

        // first.page.rename('../test-out.xhtml', __filename)
        pageInfo.resources[0].rename('../foo/bar.jpg', first.page.newPath)
        // await first.page.write()
    } else { throw new Error('BUG: expected first child in Toc to be a Page') }


    let allPages: PageFile[] = []
    const tocFiles = Array.from(factorio.tocs.all)
    for (const tocFile of tocFiles) {
        await tocFile.parse(factorio.pages, factorio.resources)
        const pages = tocFile.data.toc.map(t => tocFile.getPagesFromToc(t)).flat()
        allPages = [...allPages, ...pages]
    }

    allPages.forEach(p => p.rename(p.newPath.replace(':', '%3A'), undefined))


    tocFiles.forEach(p => p.rename(`${p.newPath}-out.xhtml`, undefined))

    for (const page of allPages) {
        await page.write()
    }
    for (const tocFile of tocFiles) {
        await tocFile.write()
        await tocFile.writeOPFFile('foo.opf')
    }
}

fn().catch(err => console.error(err))