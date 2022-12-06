// ***************************************
// Use the ../bin/epub script to run this
// ***************************************

import modulealias from 'module-alias' // From https://github.com/Microsoft/TypeScript/issues/10866#issuecomment-246929461
modulealias.addAlias('myjsx/jsx-dev-runtime', __dirname + '/minidom')

import { copyFileSync, existsSync, mkdirSync, writeFileSync } from 'fs';
import { basename, resolve } from 'path';
import { Command, InvalidArgumentError } from '@commander-js/extra-typings'
import * as sourceMapSupport from 'source-map-support';
import { ContainerFile } from './model/container';
import { factorio } from './model/factorio';
import { ResourceFile } from './model/file';
import { DIRNAMES } from './env';
sourceMapSupport.install()



const program = new Command()

program // .command('epub')
.description('Build a directory which can be zipped to create an EPUB file')
.argument('<source>', 'Source Directory. It must contain a few subdirectories like ./IO_RESOURCES/ Example: ../data/astronomy/_attic', (sourceDir: string) => {
    sourceDir = resolve(sourceDir)
    if (!existsSync(`${sourceDir}/${DIRNAMES.IO_RESOURCES}`)) throw new InvalidArgumentError(`expected ${sourceDir}/${DIRNAMES.IO_RESOURCES} to exist`)
    if (!existsSync(`${sourceDir}/${DIRNAMES.IO_FETCHED}`)) throw new InvalidArgumentError(`expected ${sourceDir}/${DIRNAMES.IO_FETCHED} to exist`)
    if (!existsSync(`${sourceDir}/${DIRNAMES.IO_BAKED}`)) throw new InvalidArgumentError(`expected ${sourceDir}/${DIRNAMES.IO_BAKED} to exist`)
    if (!existsSync(`${sourceDir}/${DIRNAMES.IO_DISASSEMBLE_LINKED}`)) throw new InvalidArgumentError(`expected ${sourceDir}/${DIRNAMES.IO_DISASSEMBLE_LINKED} to exist`)
    if (!existsSync(`${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`)) throw new InvalidArgumentError(`expected file to exist ${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`)
    return sourceDir
})
.argument('<destination>', 'Destination Directory to write the EPUB files to. Example: ./testing/', (destinationDir: string) => {
    return resolve(destinationDir)
})
.action(async (sourceDir: string, destinationDir: string) => {

    mkdirSync(destinationDir, { recursive: true })

    const booksXmlPath = `${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`
    const c = new ContainerFile(booksXmlPath)
    await c.parse(factorio)

    // Load up the models
    const tocFiles = []
    const ncxFiles = []
    for (const opfFile of factorio.opfs.all) {
        await opfFile.parse(factorio)
        await opfFile.tocFile.parse(factorio)
        await opfFile.ncxFile.parse(factorio)
        tocFiles.push(opfFile.tocFile)
        ncxFiles.push(opfFile.ncxFile)
    }
    for (const page of factorio.pages.all) {
        await page.parse(factorio)
    }
    for (const resource of factorio.resources.all) {
        await resource.parse(factorio)
    }
    const allFiles = [c, ...factorio.opfs.all, ...factorio.pages.all, ...factorio.resources.all, ...tocFiles, ...ncxFiles]

    // Rename OPF Files (they were XHTML)
    factorio.opfs.all.forEach(p => p.rename(p.newPath.replace('.xhtml', '.opf'), undefined))
    // Rename ToC files
    // Rename NCX files
    ncxFiles.forEach(p => p.rename(p.newPath.replace('.xhtml', '.ncx'), undefined))

    // Rename Page files
    factorio.pages.all.forEach(p => p.rename(p.newPath.replace(':', '-colon-'), undefined))
    factorio.pages.all.forEach(p => p.rename(p.newPath.replace('@', '-at-'), undefined))

    // Rename Resource files by adding a file extension to them
    factorio.resources.all.forEach(r => {
        const { mimeType, originalExtension } = r.parsed
        let newExtension = (ResourceFile.mimetypeExtensions)[mimeType] || originalExtension
        r.rename(`${r.newPath}.${newExtension}`, undefined)
    })


    // Specify that we will want to write all the files to a testing directory
    for (const f of allFiles) {
        f.rename(`${destinationDir}/${basename(f.newPath)}`, undefined)
    }
    c.rename(`${destinationDir}/META-INF/container.xml`, undefined)

    // Copy the CSS file to the destination
    copyFileSync(`${sourceDir}/${DIRNAMES.IO_BAKED}/the-style-pdf.css`, `${destinationDir}/the-style-epub.css`)

    writeFileSync(`${destinationDir}/mimetype`, 'application/epub+zip')
    
    for (const f of allFiles) {
        await f.write()
    }
}).parse()