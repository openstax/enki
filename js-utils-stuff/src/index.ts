// ***************************************
// Use the ../bin/epub script to run this
// ***************************************

import modulealias from 'module-alias' // From https://github.com/Microsoft/TypeScript/issues/10866#issuecomment-246929461
modulealias.addAlias('myjsx/jsx-dev-runtime', __dirname + '/minidom')

import { copyFileSync, existsSync, mkdirSync, writeFileSync } from 'fs'
import { basename, resolve } from 'path'
import { Command, InvalidArgumentError } from '@commander-js/extra-typings'
import * as sourceMapSupport from 'source-map-support'
import { ContainerFile } from './model/container'
import { factorio } from './model/factorio'
import { ResourceFile } from './model/file'
import { DIRNAMES } from './env'
sourceMapSupport.install()

const program = new Command()

program // .command('epub')
  .description('Build a directory which can be zipped to create an EPUB file')
  .argument(
    '<source>',
    'Source Directory. It must contain a few subdirectories like ./IO_RESOURCES/ Example: ../data/astronomy/_attic',
    (sourceDir: string) => {
      sourceDir = resolve(sourceDir)
      if (!existsSync(`${sourceDir}/${DIRNAMES.IO_RESOURCES}`))
        throw new InvalidArgumentError(
          `expected ${sourceDir}/${DIRNAMES.IO_RESOURCES} to exist`
        )
      if (!existsSync(`${sourceDir}/${DIRNAMES.IO_FETCHED}`))
        throw new InvalidArgumentError(
          `expected ${sourceDir}/${DIRNAMES.IO_FETCHED} to exist`
        )
      if (!existsSync(`${sourceDir}/${DIRNAMES.IO_BAKED}`))
        throw new InvalidArgumentError(
          `expected ${sourceDir}/${DIRNAMES.IO_BAKED} to exist`
        )
      if (!existsSync(`${sourceDir}/${DIRNAMES.IO_DISASSEMBLE_LINKED}`))
        throw new InvalidArgumentError(
          `expected ${sourceDir}/${DIRNAMES.IO_DISASSEMBLE_LINKED} to exist`
        )
      if (!existsSync(`${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`))
        throw new InvalidArgumentError(
          `expected file to exist ${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`
        )
      return sourceDir
    }
  )
  .argument(
    '<destination>',
    'Destination Directory to write the EPUB files to. Example: ./testing/',
    (destinationDir: string) => {
      return resolve(destinationDir)
    }
  )
  .action(async (sourceDir: string, destinationDir: string) => {
    mkdirSync(destinationDir, { recursive: true })

    const booksXmlPath = `${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`
    const c = new ContainerFile(booksXmlPath)
    await c.parse(factorio)

    // Load up the models
    for (const opfFile of factorio.opfs.all) {
      console.log(`Reading Book ${opfFile.readPath}`)
      await opfFile.parse(factorio)
      const { tocFile, ncxFile } = opfFile
      await tocFile.parse(factorio)
      await ncxFile.parse(factorio)

      for (const page of factorio.pages.all) {
        await page.parse(factorio)
      }
      for (const resource of factorio.resources.all) {
        await resource.parse(factorio)
      }
      const allFiles = [
        c,
        opfFile,
        ...factorio.pages.all,
        ...factorio.resources.all,
        tocFile,
        ncxFile,
      ]

      // Rename OPF Files (they were XHTML)
      opfFile.rename(opfFile.newPath.replace('.xhtml', '.opf'), undefined)
      // Rename ToC files
      // Rename NCX files
      ncxFile.rename(ncxFile.newPath.replace('.xhtml', '.ncx'), undefined)

      // Rename Page files
      factorio.pages.all.forEach((p) =>
        p.rename(p.newPath.replace(':', '-colon-'), undefined)
      )
      factorio.pages.all.forEach((p) =>
        p.rename(p.newPath.replace('@', '-at-'), undefined)
      )

      // Rename Resource files by adding a file extension to them
      factorio.resources.all.forEach((r) => {
        const { mimeType, originalExtension } = r.parsed
        const newExtension =
          ResourceFile.mimetypeExtensions[mimeType] || originalExtension
        r.rename(`${r.newPath}.${newExtension}`, undefined)
      })

      // Specify that we will want to write all the files to a testing directory
      for (const f of allFiles) {
        f.rename(
          `${destinationDir}/${opfFile.parsed.slug}/${basename(f.newPath)}`,
          undefined
        )
      }
      c.rename(
        `${destinationDir}/${opfFile.parsed.slug}/META-INF/container.xml`,
        undefined
      )

      const dir = `${destinationDir}/${opfFile.parsed.slug}`
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true })

      // Copy the CSS file to the destination
      copyFileSync(
        `${sourceDir}/${DIRNAMES.IO_BAKED}/the-style-pdf.css`,
        `${destinationDir}/${opfFile.parsed.slug}/the-style-epub.css`
      )

      writeFileSync(
        `${destinationDir}/${opfFile.parsed.slug}/mimetype`,
        'application/epub+zip'
      )

      // Only include the current book in the META-INF/container.xml
      // Kinda hacky way to do it
      c.parsed.splice(0, c.parsed.length)
      c.parsed.push(opfFile)

      for (const f of allFiles) {
        console.log(`Writing out ${f.newPath}`)
        await f.write()
      }

      factorio.pages.clear()
      factorio.resources.clear()
    }
  })
  .parse()
