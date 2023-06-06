// ***************************************
// Use the ../bin/bakery-helper script to run this
// ***************************************

import modulealias from 'module-alias' // From https://github.com/Microsoft/TypeScript/issues/10866#issuecomment-246929461
modulealias.addAlias('myjsx/jsx-dev-runtime', __dirname + '/minidom')

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
import { basename, join, resolve } from 'path'
import { Command, InvalidArgumentError } from '@commander-js/extra-typings'
import * as sourceMapSupport from 'source-map-support'
import { ContainerFile } from './epub/container'
import { factorio } from './epub/singletons'
import { ResourceFile } from './model/file'
import { DIRNAMES } from './env'
import {
  assertTrue,
  getPos,
  readXmlWithSourcemap,
  writeXmlWithSourcemap,
} from './utils'
import { dom } from './minidom'
import { glob } from 'glob'
sourceMapSupport.install()

const program = new Command()

const checkExists = (destinationFile: string) => {
  return resolve(destinationFile)
}

const epubSourceDirArg = program
  .createArgument(
    '<source_dir>',
    'Source Directory. It must contain a few subdirectories like ./IO_RESOURCES/ Example: ../data/astronomy/_attic'
  )
  .argParser((sourceDir: string) => {
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
  })

const epubDestinationDirArg = program
  .createArgument(
    '<destination_dir>',
    'Destination Directory to write the EPUB files to. Example: ./testing/'
  )
  .argParser(checkExists)

const epubCommand = program.command('epub')
epubCommand.description(
  'Build a directory which can be zipped to create an EPUB file'
)
epubCommand
  .addArgument(epubSourceDirArg)
  .addArgument(epubDestinationDirArg)
  .action(async (sourceDir: string, destinationDir: string) => {
    mkdirSync(destinationDir, { recursive: true })

    const booksXmlPath = `${sourceDir}/${DIRNAMES.IO_FETCHED}/META-INF/books.xml`
    const c = new ContainerFile(booksXmlPath)
    await c.parse(factorio)

    // Load up the models
    for (const opfFile of factorio.books.all) {
      console.log(`Reading Book ${opfFile.readPath}`)
      await opfFile.parse(factorio)
      const { tocFile, ncxFile } = opfFile
      await tocFile.parse(factorio)
      await ncxFile.parse(factorio)

      // Also add all Pages that are linked to by other pages (transitively reachable from the ToC)
      // Keep looping as long as we keep encountering more new Pages that are added to the list
      let foundPageCount = -1
      while (foundPageCount != (foundPageCount = factorio.pages.all.length)) {
        for (const page of factorio.pages.all) {
          await page.parse(factorio)
        }
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
      // Comment out any @import URLs though
      const cssContents = readFileSync(
        `${sourceDir}/${DIRNAMES.IO_BAKED}/the-style-pdf.css`,
        'utf-8'
      )
      writeFileSync(
        `${destinationDir}/${opfFile.parsed.slug}/the-style-epub.css`,
        cssContents.replace(
          /@import ([^\n]+)\n/g,
          '/* commented_for_epub @import $1 */\n'
        )
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

const sourceinfoSourceDirArg = program
  .createArgument(
    '<source_dir>',
    'Source Directory. It must contain CNXML and COLLXML files somewhere inside the directory'
  )
  .argParser(checkExists)
const sourceinfoDestinationDirArg = program
  .createArgument(
    '<destination_dir>',
    'Destination Directory to write the CNXML and COLLXML files to. Example: ./testing/'
  )
  .argParser(checkExists)

program
  .command('add-sourcemap-info')
  .addArgument(sourceinfoSourceDirArg)
  .addArgument(sourceinfoDestinationDirArg)
  .description(
    'Find CNXML and COLLXML files and add a data-sm attribute on them'
  )
  .action(async (sourceDir: string, destinationDir: string) => {
    const files = await glob('**/*.{cnxml,collxml}', {
      cwd: sourceDir,
    })
    assertTrue(
      files.length > 0,
      'Found 0 CNXML/COLLXML files which is unexpected'
    )
    console.log('Annotating files:', files.length)
    await Promise.all(
      files.map(async (sourceFile) => {
        const destinationFile = join(destinationDir, sourceFile)
        const $doc = dom(
          await readXmlWithSourcemap(join(sourceDir, sourceFile))
        )
        $doc.forEach('//*[not(@data-sm)]', (el) => {
          const p = getPos(el.node)
          el.attr('data-sm', `${sourceFile}:${p.lineNumber}:${p.columnNumber}`)
        })
        await writeXmlWithSourcemap(destinationFile, $doc.node)
      })
    )
  })
program.parse()
