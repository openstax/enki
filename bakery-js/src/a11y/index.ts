import { chromium, type Page } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import fs from 'node:fs'
import path from 'node:path'
import { parseXml } from '../utils'
import { dom } from '../minidom'
import { XMLSerializer } from '@xmldom/xmldom'

const log = (msg: string) => console.log(`[a11y] ${msg}`)
const logTiming = (label: string, startMs: number) =>
  log(`  ⏱ ${label}: ${((Date.now() - startMs) / 1000).toFixed(2)}s`)

const MAX_SCREENSHOTS_PER_VIOLATION = 50
const SCREENSHOT_PADDING = 50
const SCREENSHOT_MAX_HEIGHT = 600

const DEFAULT_TAGS = ['wcag2a', 'wcag21a', 'wcag2aa', 'wcag21aa']

const AXE_TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes

const analyzePage = async (page: Page, inputFile: string, tags?: string[]) => {
  const label = path.basename(inputFile)
  const filePath = `file://${inputFile}`

  // Fail fast if the renderer crashes (e.g. OOM) rather than hanging forever
  const crashPromise = new Promise<never>((_, reject) => {
    page.once('crash', () =>
      reject(new Error(`Chromium renderer crashed for ${label}`))
    )
  })

  let t = Date.now()
  await Promise.race([
    page.goto(filePath, { waitUntil: 'domcontentloaded' }),
    crashPromise,
  ])
  logTiming(`page.goto (domcontentloaded) [${label}]`, t)

  t = Date.now()
  const axePromise = new AxeBuilder({ page })
    .withTags(tags ?? DEFAULT_TAGS)
    .analyze()
  const timeoutPromise = new Promise<never>((_, reject) =>
    setTimeout(
      () =>
        reject(
          new Error(
            `axe-core timed out after ${AXE_TIMEOUT_MS / 1000}s for ${label}`
          )
        ),
      AXE_TIMEOUT_MS
    )
  )
  const result = await Promise.race([axePromise, timeoutPromise, crashPromise])
  logTiming(`axe-core analysis [${label}]`, t)

  return result
}

type AnalyzeResult = Awaited<ReturnType<typeof analyzePage>>

type ScreenshotMap = Record<string, string>
type SourceMap = Record<string, string>

const captureViolationScreenshots = async (
  page: Page,
  results: AnalyzeResult,
  maxPerViolation = MAX_SCREENSHOTS_PER_VIOLATION
): Promise<ScreenshotMap> => {
  const screenshots: ScreenshotMap = {}

  for (const violation of results.violations) {
    const nodesToCapture = violation.nodes.slice(0, maxPerViolation)
    const tViolation = Date.now()
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
    if (nodesToCapture.length > 0) {
      logTiming(
        `screenshots for "${violation.id}" (${nodesToCapture.length} nodes)`,
        tViolation
      )
    }
  }

  return screenshots
}

const captureSourceMapData = async (
  page: Page,
  results: AnalyzeResult
): Promise<SourceMap> => {
  const sourceMap: SourceMap = {}

  for (const violation of results.violations) {
    const t = Date.now()
    const nodeCount = violation.nodes.length
    for (let i = 0; i < nodeCount; i++) {
      const node = violation.nodes[i]
      const selector = node.target[0]
      if (typeof selector !== 'string') continue

      const sm = await page.evaluate((sel) => {
        const el = document.querySelector(sel)
        if (!el) return null
        // Walk up ancestors and their subtrees trying to find nearest data-sm
        let current: Element | null = el
        while (current) {
          const val =
            current.getAttribute('data-sm') ??
            current.querySelector('[data-sm]')?.getAttribute('data-sm')
          if (val) return val
          current = current.parentElement
        }
        return null
      }, selector)

      if (sm !== null) sourceMap[`${violation.id}-${i}`] = sm
    }
    logTiming(`source map for "${violation.id}" (${nodeCount} nodes)`, t)
  }

  return sourceMap
}

interface FileResult {
  file: string
  results: AnalyzeResult
  screenshots: ScreenshotMap
  sourceMap: SourceMap
}

// Parses a data-sm value like ./modules/m59760/index.cnxml:24:1 into a GitHub URL
const smToGithubUrl = (
  sm: string,
  repo: string,
  ref: string
): string | null => {
  const match = sm.match(/^(?:\.\/)?(.+):(\d+):\d+$/)
  if (!match) return null
  const [, filePath, line] = match
  const fullRepo = repo.includes('/') ? repo : `openstax/${repo}`
  return `https://github.com/${fullRepo}/blob/${ref}/${filePath}#L${line}`
}

const formatWcagCriteria = (tags: string[]): string => {
  return tags
    .filter((t) => /^wcag\d{3,}$/.test(t))
    .map((t) => {
      const d = t.slice(4)
      if (d.length === 3) return `${d[0]}.${d[1]}.${d[2]}`
      if (d.length === 4) return `${d[0]}.${d[1]}.${d.slice(2)}`
      return d
    })
    .join(', ')
}

const escapeHtml = (str: string) =>
  str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const generateSummary = (
  fileResults: FileResult[],
  repo?: string,
  ref = 'main'
) => {
  let body = ''
  const head =
    '<style>' +
    'td, th { padding: 10px; border: 2px dotted; } ' +
    'img.a11y-screenshot { max-width: 600px; border: 1px solid #ccc; margin-top: 8px; }' +
    '</style>'

  for (const { file, results, screenshots, sourceMap } of fileResults) {
    body += `<h2>${escapeHtml(path.basename(file))}</h2>\n`

    if (results.violations.length === 0) {
      body += '<h3>✅ All Checks Passed!</h3>\n<p>No issues found.</p>\n'
    } else {
      body += `<h3>❌ Found ${results.violations.length} Violation Types</h3>\n`
      body +=
        '<table>\n<thead><tr><th>Impact</th><th>Description</th><th>WCAG</th><th>GitHub</th><th>Elements Affected</th></tr></thead>\n<tbody>\n'

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
          const sm = sourceMap[`${v.id}-${nodeIdx}`]
          const githubUrl =
            repo !== undefined && sm ? smToGithubUrl(sm, repo, ref) : null
          const githubHtml = githubUrl
            ? `<a href="${escapeHtml(githubUrl)}" target="_blank">${escapeHtml(
                sm
              )}</a>`
            : 'N/A'
          const wcagCriteria = formatWcagCriteria(v.tags)
          const wcagHtml = wcagCriteria
            ? `<a href="${escapeHtml(v.helpUrl)}" target="_blank">${escapeHtml(
                wcagCriteria
              )}</a>`
            : `<a href="${escapeHtml(v.helpUrl)}" target="_blank">${escapeHtml(
                v.id
              )}</a>`
          body += `<tr><td><strong>${escapeHtml(
            v.impact?.toUpperCase() ?? ''
          )}</strong></td><td>${escapeHtml(
            v.help
          )}</td><td>${wcagHtml}</td><td>${githubHtml}</td><td>${escapeHtml(
            node.target.join(', ')
          )}${screenshotHtml}</td></tr>\n`
        })
      })

      body += '</tbody>\n</table>\n'
    }
  }

  return `<html><head>${head}</head><body>${body}</body></html>`
}

interface A11yOptions {
  inputFiles: string[]
  tags?: string[]
  repo?: string
  ref?: string
  fraction?: number
  maxChapters?: number
  maxPagesPerChapter?: number
  maxParallel?: number
}

// Runs tasks with at most maxConcurrency running simultaneously, preserving result order.
const runWithConcurrency = async <T>(
  tasks: Array<() => Promise<T>>,
  maxConcurrency: number
): Promise<T[]> => {
  const results: T[] = new Array(tasks.length)
  let next = 0
  const worker = async () => {
    while (next < tasks.length) {
      const i = next++
      results[i] = await tasks[i]()
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(maxConcurrency, tasks.length) }, worker)
  )
  return results
}

const makeLazy = (doc: Document) => {
  const loadable = dom(doc).find(
    '//*[local-name() = "img" or local-name() = "iframe"]'
  )
  loadable.forEach((node) => {
    node.attr('loading', 'lazy')
  })
}

const shorten = (
  inputFile: string,
  fraction = 0.25,
  maxChapters?: number,
  maxPagesPerChapter?: number
): string => {
  let t = Date.now()
  const content = fs.readFileSync(inputFile, 'utf-8')
  const fileSizeMb = (
    Buffer.byteLength(content, 'utf-8') /
    1024 /
    1024
  ).toFixed(1)
  log(`File size: ${fileSizeMb} MB`)
  logTiming('read file', t)

  t = Date.now()
  const doc = parseXml(content)
  logTiming('parse XML', t)

  const chapters = dom(doc).find('//*[@data-type="chapter"]')

  if (chapters.length === 0) {
    log(`No chapters found in ${inputFile}, skipping shortening`)
    return inputFile
  }

  const effectiveFraction =
    maxChapters !== undefined ? maxChapters / chapters.length : fraction
  const step = Math.max(1, Math.round(1 / effectiveFraction))
  const keep = new Set(chapters.filter((_, i) => i % step === 0))

  let totalPagesRemoved = 0
  let totalPagesKept = 0

  for (const chapter of chapters) {
    if (!keep.has(chapter)) {
      chapter.remove()
    } else if (maxPagesPerChapter) {
      const pages = chapter.find('.//*[@data-type="page"]')
      const toRemove = pages.slice(maxPagesPerChapter)
      toRemove.forEach((page) => {
        page.remove()
      })
      totalPagesRemoved += toRemove.length
      totalPagesKept += pages.length - toRemove.length
    }
  }

  // Strip MathML — axe-core has no applicable WCAG rules for math content,
  // but traversing thousands of deeply-nested MathML trees dominates analysis time.
  const mathElements = dom(doc).find('//*[local-name() = "math"]')
  mathElements.forEach((el) => el.remove())

  // Strip footnotes — these are moved elsewhere in the PDF/web pipeline,
  // so violations here are false positives.
  const footnotes = dom(doc).find(
    '//*[local-name() = "aside" and @role="doc-footnote"]'
  )
  footnotes.forEach((el) => el.remove())

  makeLazy(doc)

  t = Date.now()
  const serializer = new XMLSerializer()
  const xml = serializer.serializeToString(doc)
  logTiming('serialize XML', t)

  const shortenedSizeMb = (
    Buffer.byteLength(xml, 'utf-8') /
    1024 /
    1024
  ).toFixed(1)
  log(
    `Shortened ${path.basename(inputFile)}: kept ${keep.size}/${
      chapters.length
    } chapters` +
      (maxPagesPerChapter
        ? `, ${totalPagesKept} pages kept / ${totalPagesRemoved} pages removed (${maxPagesPerChapter} max/chapter)`
        : '') +
      `, stripped ${mathElements.length} math + ${footnotes.length} footnote elements` +
      ` (${fileSizeMb} MB -> ${shortenedSizeMb} MB)`
  )

  t = Date.now()
  const dir = path.dirname(inputFile)
  const base = path.basename(inputFile, path.extname(inputFile))
  const tmpFile = path.join(dir, `${base}.a11y-shortened.xhtml`)
  fs.writeFileSync(tmpFile, xml, 'utf-8')
  logTiming('write shortened file', t)

  return tmpFile
}

export const run = async (options: A11yOptions) => {
  const tTotal = Date.now()

  // Shorten all files sequentially so the XML DOM for each can be GC'd before
  // the next parse begins, keeping peak Node.js memory to a single file at a time.
  const shortenedFiles = options.inputFiles.map((inputFile, i) => {
    log(`Shortening file ${i + 1}/${options.inputFiles.length}: ${inputFile}`)
    return {
      inputFile,
      shortened: shorten(
        inputFile,
        options.fraction,
        options.maxChapters,
        options.maxPagesPerChapter
      ),
    }
  })

  const maxParallel = options.maxParallel ?? 2
  log(
    `Launching browser for ${options.inputFiles.length} file(s), max ${maxParallel} in parallel...`
  )
  const browser = await chromium.launch({ timeout: 60_000 * 5 })
  const browserContext = await browser.newContext()

  try {
    const fileResults = await runWithConcurrency(
      shortenedFiles.map(({ inputFile, shortened }, i) => async () => {
        const page = await browserContext.newPage()
        const tFile = Date.now()
        log(
          `Analyzing file ${i + 1}/${options.inputFiles.length}: ${inputFile}`
        )
        try {
          const results = await analyzePage(page, shortened, options.tags)
          const violationCount = results.violations.length
          const totalNodes = results.violations.reduce(
            (sum, v) => sum + v.nodes.length,
            0
          )
          let screenshots: ScreenshotMap = {}
          let sourceMap: SourceMap = {}
          if (violationCount === 0) {
            log(`No violations found in ${path.basename(inputFile)}`)
          } else {
            log(
              `Found ${violationCount} violation types across ${totalNodes} nodes in ${path.basename(
                inputFile
              )}`
            )
            log('Capturing screenshots of violations...')
            const tScreenshots = Date.now()
            screenshots = await captureViolationScreenshots(page, results)
            logTiming(
              `screenshots total (${Object.keys(screenshots).length} captured)`,
              tScreenshots
            )
            const tSourceMap = Date.now()
            sourceMap = await captureSourceMapData(page, results)
            logTiming(`source map total (${totalNodes} nodes)`, tSourceMap)
          }
          logTiming(`file ${i + 1} total`, tFile)
          return { file: inputFile, results, screenshots, sourceMap }
        } finally {
          if (shortened !== inputFile) {
            fs.unlinkSync(shortened)
          }
          await page.close()
        }
      }),
      maxParallel
    )

    logTiming('all files total', tTotal)
    log(`Done. Tested ${fileResults.length} files`)
    return generateSummary(fileResults, options.repo, options.ref)
  } finally {
    await browser.close()
  }
}
