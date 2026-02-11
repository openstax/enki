import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import fs from 'node:fs'
import path from 'node:path'
import { parseXml } from '../utils'
import { dom } from '../minidom'
import { XMLSerializer } from '@xmldom/xmldom'

const log = (msg: string) => console.log(`[a11y] ${msg}`)

const getPlaywrightContext = async () => {
  log('Launching browser...')
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  return { browser, context, page }
}

type PlaywrightContext = Awaited<ReturnType<typeof getPlaywrightContext>>
const DEFAULT_TAGS = ['wcag2aa', 'wcag21aa']

const analyzePage = async ({
  page,
  inputFile,
  tags,
}: PlaywrightContext & { inputFile: string; tags?: string[] }) => {
  const filePath = `file://${inputFile}`
  await page.goto(filePath)
  return await new AxeBuilder({ page }).withTags(tags ?? DEFAULT_TAGS).analyze()
}

type AnalyzeResult = Awaited<ReturnType<typeof analyzePage>>

interface FileResult {
  file: string
  results: AnalyzeResult
}

const generateSummary = (fileResults: FileResult[]) => {
  let body = ''
  const head = '<style>td, th { padding: 10px; border: 2px dotted; }</style>'

  for (const { file, results } of fileResults) {
    body += `<h2>${file}</h2>\n`

    if (results.violations.length === 0) {
      body += '<h3>✅ All Checks Passed!</h3>\n<p>No issues found.</p>\n'
    } else {
      body += `<h3>❌ Found ${results.violations.length} Violation Types</h3>\n`
      body +=
        '<table>\n<thead><tr><th>Impact</th><th>Description</th><th>Elements Affected</th></tr></thead>\n<tbody>\n'

      results.violations.forEach((v) => {
        v.nodes.forEach((node) => {
          body += `<tr><td><strong>${v.impact?.toUpperCase()}</strong></td><td>${
            v.help
          }</td><td>${node.target}</td></tr>\n`
        })
      })

      body += '</tbody>\n</table>\n'
    }
  }

  return `<html><head>${head}</head><body>${body}</body></html>`
}

interface A11yOptions {
  inputFiles: string[]
  outputDir: string
  tags?: string[]
}

const shorten = (inputFile: string, fraction = 0.25): string => {
  const content = fs.readFileSync(inputFile, 'utf-8')
  const doc = parseXml(content)
  const chapters = dom(doc).find('//*[@data-type="chapter"]')

  if (chapters.length === 0) {
    log(`No chapters found in ${inputFile}, skipping shortening`)
    return inputFile
  }

  const step = Math.max(1, Math.round(1 / fraction))
  const keep = new Set(chapters.filter((_, i) => i % step === 0))

  for (const chapter of chapters) {
    if (!keep.has(chapter)) {
      chapter.remove()
    }
  }

  const serializer = new XMLSerializer()
  const xml = serializer.serializeToString(doc)
  const dir = path.dirname(inputFile)
  const base = path.basename(inputFile, path.extname(inputFile))
  const tmpFile = path.join(dir, `${base}.a11y-shortened.xhtml`)
  fs.writeFileSync(tmpFile, xml, 'utf-8')
  log(`Shortened ${inputFile}: kept ${keep.size}/${chapters.length} chapters`)
  return tmpFile
}

export const run = async (options: A11yOptions) => {
  const context = await getPlaywrightContext()
  const fileResults: FileResult[] = []
  try {
    for (let i = 0; i < options.inputFiles.length; i++) {
      const inputFile = options.inputFiles[i]
      log(`Analyzing file ${i + 1}/${options.inputFiles.length}: ${inputFile}`)
      const shortened = shorten(inputFile)
      try {
        const results = await analyzePage({
          ...context,
          inputFile: shortened,
          tags: options.tags,
        })
        const violationCount = results.violations.length
        if (violationCount === 0) {
          log(`No violations found`)
        } else {
          log(`Found ${violationCount} violation types`)
        }
        fileResults.push({ file: inputFile, results })
      } finally {
        if (shortened !== inputFile) {
          fs.unlinkSync(shortened)
        }
      }
    }
    log(`Done. Tested ${fileResults.length} files`)
    return generateSummary(fileResults)
  } finally {
    await context.browser.close()
  }
}
