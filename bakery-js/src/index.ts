// ***************************************
// Use the ../bin/bakery-helper script to run this
// ***************************************

import modulealias from 'module-alias' // From https://github.com/Microsoft/TypeScript/issues/10866#issuecomment-246929461
modulealias.addAlias('myjsx/jsx-dev-runtime', __dirname + '/minidom')

import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  copyFileSync,
  constants,
  promises,
} from 'fs'
import { basename, dirname, resolve } from 'path'
import { Command, InvalidArgumentError } from '@commander-js/extra-typings'
import * as sourceMapSupport from 'source-map-support'
import { ContainerFile } from './epub/container'
import { factorio } from './epub/singletons'
import { ResourceFile } from './model/file'
import { DIRNAMES } from './env'
import { getPos, readXmlWithSourcemap, writeXmlWithSourcemap } from './utils'
import { dom } from './minidom'
import Ajv from 'ajv'
import { createInterface } from 'readline'
sourceMapSupport.install()

const coverPage = `<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Cover</title>
    <style type="text/css">
        body.fullpage {
            margin: 0;
            padding: 0;
        }

        section.cover {
            display: block;
            text-align: center;
            height: 95%;
        }

        img#coverimage {
            height: 95%;
        }

        img#coverimage:only-of-type {
            /*overrides the previous setting, but only in newer systems that support CSS3 */
            height: 95vh;
        }
    </style>
</head>
<body class="fullpage">
    <section epub:type="cover" class="cover">
        <img id="coverimage" src="cover.jpg" alt="cover image" />
    </section>
</body>
</html>`

const program = new Command()

const sourceDirArg = program
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

const destinationDirArg = program
  .createArgument(
    '<destination_dir>',
    'Destination Directory to write the EPUB files to. Example: ./testing/'
  )
  .argParser((destinationDir: string) => {
    return resolve(destinationDir)
  })

const epubCommand = program.command('epub')
epubCommand.description(
  'Build a directory which can be zipped to create an EPUB file'
)
epubCommand
  .addArgument(sourceDirArg)
  .addArgument(destinationDirArg)
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
        if (!r.newPath.endsWith(`.${newExtension}`)) {
          r.rename(`${r.newPath}.${newExtension}`, undefined)
        }
      })

      // Ignore the directory that the files were in and instead put al lthe files in a single directory named {destinationDir}/{slug}
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

      opfFile.parsed.allFonts.forEach((f) => {
        f.rename(
          `${dirname(f.newPath)}/downloaded-fonts/${basename(f.newPath)}`
        )
      })

      const dir = `${destinationDir}/${opfFile.parsed.slug}`
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true })

      // Copy the CSS file to the destination
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

      // cover
      if (opfFile.parsed.coverFile) {
        const newCoverFile = `${destinationDir}/${opfFile.parsed.slug}/cover.jpg`
        console.log(`Writing out ${newCoverFile}`)
        try {
          copyFileSync(
            opfFile.parsed.coverFile,
            newCoverFile,
            constants.COPYFILE_EXCL
          )
        } catch (error: any) {
          /* istanbul ignore next */
          if (error.code == 'EEXIST')
            console.warn(`File already exists! ${newCoverFile}`)
          else throw error
        }
        writeFileSync(
          `${destinationDir}/${opfFile.parsed.slug}/cover.xhtml`,
          coverPage
        )
      }

      factorio.pages.clear()
      factorio.resources.clear()
    }
  })

const sourceFileArg = program.createArgument(
  '<source_file>',
  'Source XML filename (e.g. modules/m123/index.cnxml'
)
const destinationFileArg = program.createArgument(
  '<destination_file>',
  'Destination XML filename (e.g. modules/m123/index.cnxml'
)

program
  .command('add-sourcemap-info')
  .addArgument(sourceFileArg)
  .addArgument(destinationFileArg)
  .action(async (sourceFile: string, destinationFile: string) => {
    const $doc = dom(await readXmlWithSourcemap(sourceFile))
    $doc.forEach('//*[not(@data-sm)]', (el) => {
      const p = getPos(el.node)
      el.attr('data-sm', `${sourceFile}:${p.lineNumber}:${p.columnNumber}`)
    })
    await writeXmlWithSourcemap(destinationFile, $doc.node)
  })

const schemaArg = program.createArgument(
  '<schema_file>',
  'The schema file to validate against (e.g. schemas/book-schema.json)'
)

program
  .command('jsonschema')
  .description(
    'Validate a list of files piped in on stdin against a json schema'
  )
  .addArgument(schemaArg)
  .action(async (schemaFile: string) => {
    const ajv = new Ajv({ allErrors: true, verbose: true })
    const schema = JSON.parse(readFileSync(schemaFile, { encoding: 'utf-8' }))
    const validate = ajv.compile(schema)
    const readline = createInterface({ input: process.stdin })
    for await (const line of readline) {
      process.stderr.write(`Validating ${line}\n`)
      promises
        .readFile(line, { encoding: 'utf-8' })
        .then((data) => {
          if (!validate(JSON.parse(data))) {
            const output = {
              file: line,
              errors: validate.errors,
            }
            process.stdout.write(JSON.stringify(output, null, 2))
            process.exitCode = 1
          }
        })
        .catch((err) => {
          throw err
        })
    }
  })

program.parse()
