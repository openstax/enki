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
import { upload } from './ancillary-integration'
import { run as runA11y } from './a11y'
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
        `${sourceDir}/${DIRNAMES.IO_BAKED}/${opfFile.parsed.slug}-pdf.css`,
        'utf-8'
      )
      // NOTE: Each css file has the same name in a different book directory
      writeFileSync(
        `${destinationDir}/${opfFile.parsed.slug}/the-style-epub.css`,
        cssContents
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

const inplaceOption = program.createOption(
  '-i, --in-place',
  'Modify the file in-place'
)

async function* progressSpinner<T>(iter: AsyncIterable<T> | Iterable<T>) {
  const spinner = '\\|/-'
  let i = 0
  // Move right 1 and save position
  process.stderr.write('\u001b[1C')
  process.stderr.write('\u001b[s')
  for await (const item of iter) {
    // Restore position
    process.stderr.write('\u001b[u')
    process.stderr.write(`${spinner[i++ % spinner.length]} `)
    yield item
  }
  process.stderr.write('\n')
}

program
  .command('add-sourcemap-info')
  .addOption(inplaceOption)
  .action(async (options) => {
    const log = (msg: string) => process.stderr.write(msg)
    const inPlace = options.inPlace !== undefined
    const readline = createInterface({ input: process.stdin })
    log('Annotating XML files with source map information (data-sm="...")')
    for await (const sourceFile of progressSpinner(readline)) {
      try {
        const destinationFile = inPlace ? sourceFile : `${sourceFile}.mapped`
        const $doc = dom(await readXmlWithSourcemap(sourceFile))
        $doc.forEach('//*[not(@data-sm)]', (el) => {
          const p = getPos(el.node)
          el.attr('data-sm', `${sourceFile}:${p.lineNumber}:${p.columnNumber}`)
        })
        await writeXmlWithSourcemap(destinationFile, $doc.node)
      } catch (e) {
        log(`\n[ERROR] Failed to annotate ${sourceFile}: ${e}\n`)
      }
    }
    log('XML files annotated successfully!\n')
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

program
  .command('ancillary')
  .argument('<ancillaries-dir>', 'directory containing ancillaries to upload')
  .action(async (ancillariesDir) => {
    await upload(ancillariesDir)
  })

program
  .command('a11y')
  .description('Run accessibility tests on baked XHTML files')
  .argument('<output-dir>', 'Directory to write the HTML report to')
  .argument('<input-files...>', 'Baked XHTML files to test')
  .option('-t, --tags <tags...>', 'axe-core rule tags to test', [
    'wcag2a',
    'wcag21a',
    'wcag2aa',
    'wcag21aa',
  ])
  .option(
    '-r, --repo <repo>',
    'GitHub repository name for source links (e.g. osbooks-physics)'
  )
  .option('-R, --ref <ref>', 'Git ref or SHA for GitHub source links', 'main')
  .option(
    '-f, --fraction <fraction>',
    'Fraction of chapters to keep when shortening books (default: 0.25)',
    parseFloat
  )
  .action(async (outputDir, inputFiles, options) => {
    outputDir = resolve(outputDir)
    mkdirSync(outputDir, { recursive: true })
    const summary = await runA11y({
      inputFiles: inputFiles.map((f: string) => resolve(f)),
      tags: options.tags,
      repo: options.repo,
      ref: options.ref,
      fraction: options.fraction,
    })
    const reportPath = `${outputDir}/a11y-report.html`
    writeFileSync(reportPath, summary)
    console.log(`Report written to ${reportPath}`)
  })

program.parse()
