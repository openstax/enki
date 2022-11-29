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
    await c.parse(factorio.pages, factorio.resources, factorio.tocs)
    c.rename(`${join(__dirname, '../testing')}/container.xml`, undefined)

    // Load up the models
    for (const tocFile of factorio.tocs.all) {
        await tocFile.parse(factorio.pages, factorio.resources, factorio.tocs)
    }
    for (const page of factorio.pages.all) {
        await page.parse(factorio.pages, factorio.resources, factorio.tocs)
    }
    for (const resource of factorio.resources.all) {
        await resource.parse(factorio.pages, factorio.resources, factorio.tocs)
    }
    const allFiles = [c, ...factorio.tocs.all, ...factorio.pages.all, ...factorio.resources.all]

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
    for (const tocFile of factorio.tocs.all) {
        await tocFile.writeOPFFile(`${tocFile.newPath}.opf`)
    }
}

fn().catch(err => console.error(err))