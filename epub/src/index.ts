import { copyFileSync } from 'fs';
import { basename, join, resolve } from 'path';
import * as sourceMapSupport from 'source-map-support';
import { ContainerFile } from './model/container';
import { factorio } from './model/factorio';
import { ResourceFile } from './model/file';
import { assertValue } from './utils';

sourceMapSupport.install()

async function fn() {

    const dataDirPath = process.argv[2]
    assertValue(dataDirPath, 'Missing console parameter. specify something like ../data/astronomy/_attic (something that contains IO_FETCHED/META-INF/books.xml, IO_RESOURCES/ , IO_DISASSEMBLED/ , ')

    const booksXmlPath = `${dataDirPath}/IO_FETCHED/META-INF/books.xml`
    const c = new ContainerFile(resolve(booksXmlPath))
    await c.parse(factorio.pages, factorio.resources, factorio.opfs)
    c.rename(`${join(__dirname, '../testing')}/container.xml`, undefined)

    // Load up the models
    const tocFiles = []
    const ncxFiles = []
    for (const opfFile of factorio.opfs.all) {
        await opfFile.parse(factorio.pages, factorio.resources, factorio.opfs)
        await opfFile.tocFile.parse(factorio.pages, factorio.resources, factorio.opfs)
        await opfFile.ncxFile.parse(factorio.pages, factorio.resources, factorio.opfs)
        tocFiles.push(opfFile.tocFile)
        ncxFiles.push(opfFile.ncxFile)
    }
    for (const page of factorio.pages.all) {
        await page.parse(factorio.pages, factorio.resources, factorio.opfs)
    }
    for (const resource of factorio.resources.all) {
        await resource.parse(factorio.pages, factorio.resources, factorio.opfs)
    }
    const allFiles = [c, ...factorio.opfs.all, ...factorio.pages.all, ...factorio.resources.all, ...tocFiles, ...ncxFiles]

    // Rename OPF Files (they were XHTML)
    Array.from(factorio.opfs.all).forEach(p => p.rename(p.newPath.replace('.xhtml', '.opf'), undefined))
    // Rename ToC files
    // Rename NCX files
    Array.from(ncxFiles).forEach(p => p.rename(p.newPath.replace('.xhtml', '.ncx'), undefined))

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

    // Copy the CSS file to the destination
    copyFileSync(`${dataDirPath}/IO_BAKED/the-style-pdf.css`, `${join(__dirname, '../testing')}/the-style-epub.css`)
    
    for (const f of allFiles) {
        await f.write()
    }
}

fn().catch(err => console.error(err))