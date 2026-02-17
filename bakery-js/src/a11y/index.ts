import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import fs from 'node:fs'
import path from 'node:path'
import { parseXml } from '../utils'
import { dom } from '../minidom'
import { XMLSerializer } from '@xmldom/xmldom'

const log = (msg: string) => console.log(`[a11y] ${msg}`)

const MAX_SCREENSHOTS_PER_VIOLATION = 50
const SCREENSHOT_PADDING = 50
const SCREENSHOT_MAX_HEIGHT = 600

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

type ScreenshotMap = Record<string, string>

const captureViolationScreenshots = async (
  page: PlaywrightContext['page'],
  results: AnalyzeResult,
  maxPerViolation = MAX_SCREENSHOTS_PER_VIOLATION
): Promise<ScreenshotMap> => {
  const screenshots: ScreenshotMap = {}

  for (const violation of results.violations) {
    const nodesToCapture = violation.nodes.slice(0, maxPerViolation)
    for (let i = 0; i < nodesToCapture.length; i++) {
      const node = nodesToCapture[i]
      const selector = node.target[0]
      if (typeof selector !== 'string') continue

      try {
        const el = page.locator(selector).first()
        await el.scrollIntoViewIfNeeded()

        await el.evaluate((e) => {
          const h = e as HTMLElement
          h.style.outline = '3px solid red'
          h.style.outlineOffset = '2px'
        })

        let buffer: Buffer
        const box = await el.boundingBox()
        if (box) {
          const clip = {
            x: Math.max(0, box.x - SCREENSHOT_PADDING),
            y: Math.max(0, box.y - SCREENSHOT_PADDING),
            width: box.width + SCREENSHOT_PADDING * 2,
            height: Math.min(
              box.height + SCREENSHOT_PADDING * 2,
              SCREENSHOT_MAX_HEIGHT
            ),
          }
          buffer = await page.screenshot({ clip })
        } else {
          buffer = await el.screenshot()
        }

        await el.evaluate((e) => {
          const h = e as HTMLElement
          h.style.outline = ''
          h.style.outlineOffset = ''
        })

        screenshots[`${violation.id}-${i}`] = buffer.toString('base64')
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        log(`Could not screenshot element for "${violation.id}": ${msg}`)
      }
    }
  }

  return screenshots
}

interface FileResult {
  file: string
  results: AnalyzeResult
  screenshots: ScreenshotMap
}

const generateSummary = (fileResults: FileResult[]) => {
  let body = ''
  const head =
    '<style>' +
    'td, th { padding: 10px; border: 2px dotted; } ' +
    'img.a11y-screenshot { max-width: 600px; border: 1px solid #ccc; margin-top: 8px; }' +
    '</style>'

  for (const { file, results, screenshots } of fileResults) {
    body += `<h2>${file}</h2>\n`

    if (results.violations.length === 0) {
      body += '<h3>✅ All Checks Passed!</h3>\n<p>No issues found.</p>\n'
    } else {
      body += `<h3>❌ Found ${results.violations.length} Violation Types</h3>\n`
      body +=
        '<table>\n<thead><tr><th>Impact</th><th>Description</th><th>Elements Affected</th></tr></thead>\n<tbody>\n'

      results.violations.forEach((v) => {
        v.nodes.forEach((node, nodeIdx) => {
          const screenshotB64 = screenshots[`${v.id}-${nodeIdx}`]
          let screenshotHtml = ''
          if (screenshotB64) {
            screenshotHtml =
              '<details><summary>Screenshot</summary>' +
              '<img class="a11y-screenshot" ' +
              `src="data:image/png;base64,${screenshotB64}" ` +
              'alt="Screenshot of violation"/></details>'
          }
          body += `<tr><td><strong>${v.impact?.toUpperCase()}</strong></td><td>${
            v.help
          }</td><td>${node.target}${screenshotHtml}</td></tr>\n`
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
        let screenshots: ScreenshotMap = {}
        if (violationCount === 0) {
          log(`No violations found`)
        } else {
          log(`Found ${violationCount} violation types`)
          log('Capturing screenshots of violations...')
          screenshots = await captureViolationScreenshots(context.page, results)
          log(`Captured ${Object.keys(screenshots).length} screenshots`)
        }
        fileResults.push({ file: inputFile, results, screenshots })
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
