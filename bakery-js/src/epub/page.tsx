import { existsSync } from 'fs'
import { dirname, resolve } from 'path'
import { Dom, dom } from '../minidom'
import { assertTrue, assertValue, getPos, Pos } from '../utils'
import type { Factorio } from '../model/factorio'
import type { Factory } from '../model/factory'
import { ResourceFile, XmlFile } from '../model/file'
import { OpfFile } from './toc'

const RESOURCE_SELECTORS: Array<[string, string]> = [
  ['//h:img', 'src'],
  ['//h:a[starts-with(@href, "../resources/")]', 'href'],
  ['//h:object', 'data'],
  ['//h:embed', 'src'],
]

export type PageData = {
  title: string
  hasMathML: boolean
  hasRemoteResources: boolean
  pageLinks: PageFile[]
  resources: ResourceFile[]
}

// The title of the chapter/unit this page is the first page of, if any.
// Set externally (see toc.tsx's markStructuralPageRoles / findFirstPage),
// and inserted as a leading h1 in convert() so the page's own heading
// structure descends from a real ancestor instead of starting mid-tree.
export type AncestorTitle = {
  title: string
  pos: Pos
}

// Set externally by toc.tsx's markStructuralPageRoles for the first page
// of a structural unit (chapter/unit/preface/appendix/index). `label` is
// null for tocTargetType-driven roles (preface/appendix/index) - those
// are set before this page has parsed its own title, so convert() falls
// back to this.parsed.title instead.
export type AriaSpec = {
  role: string
  label: string | null
}

// The epub:type structural-semantics vocabulary term for each ARIA role
// convert() may write. Kept explicit rather than derived from the role
// string (e.g. stripping "doc-") since that pattern isn't guaranteed to
// hold for roles not yet in use here.
const EPUB_TYPE_BY_ARIA_ROLE: Record<string, string> = {
  'doc-part': 'part',
  'doc-chapter': 'chapter',
  'doc-preface': 'preface',
  'doc-appendix': 'appendix',
  'doc-index': 'index',
}

function filterNulls<T>(l: Array<T | null>): Array<T> {
  const ret: T[] = []
  for (const i of l) {
    if (i !== null) ret.push(i)
  }
  return ret
}

const pageLinkXpath =
  '//h:a[@href and not(starts-with(@href, "http:") or starts-with(@href, "https:") or starts-with(@href, "#"))]'

export class PageFile extends XmlFile<
  PageData,
  OpfFile,
  PageFile,
  ResourceFile
> {
  public ariaSpec: AriaSpec | null = null
  public ancestorTitle: AncestorTitle | null = null
  async parse(
    factorio: Factorio<OpfFile, PageFile, ResourceFile>
  ): Promise<void> {
    if (this._parsed !== undefined) return // Only parse once
    const doc = dom(await this.readXml(this.readPath))
    const pageLinks = filterNulls(
      doc.map(pageLinkXpath, (a) => {
        const u = new URL(
          assertValue(a.attr('href')),
          'https://example-i-am-not-really-used.com'
        )
        const pagePathRel = u.pathname.slice(1) // remove leading slash
        const pagePathAbs = resolve(dirname(this.readPath), pagePathRel)
        /* istanbul ignore if */
        if (pagePathRel.length === 0 || !existsSync(pagePathAbs)) {
          const pos = getPos(a.node)
          console.warn(
            `WARN: Invalid link '${a.attr('href')}' Source: ${
              pos.source.fileName
            }:${pos.lineNumber}:${pos.columnNumber}`
          )
          return null
        }
        return factorio.pages.getOrAdd(pagePathRel, this.readPath)
      })
    )
    const resources = RESOURCE_SELECTORS.map(([sel, attrName]) =>
      this.resourceFinder(factorio.resources, doc, sel, attrName)
    ).flat()

    const selectors = [
      '//h:h1[@data-type="document-title"]',
      '//h:h2[@data-type="document-title"]',
      '//h:html/h:body/h:div[@data-type="composite-page"]/h:h3[@data-type="title"]',
    ]
    const titleNode =
      doc.find(selectors[0])[0] ||
      doc.find(selectors[1])[0] ||
      doc.find(selectors[2])[0]
    const title = titleNode === undefined ? 'untitled' : titleNode.text()
    this._parsed = {
      title,
      hasMathML: doc.has('//m:math|//h:math'),
      hasRemoteResources: doc.has('//h:iframe|//h:object/h:embed'),
      pageLinks,
      resources,
    }
  }
  private resourceFinder(
    resourceFactory: Factory<ResourceFile>,
    node: Dom,
    sel: string,
    attrName: string
  ) {
    return node.map(sel, (img) =>
      resourceFactory.getOrAdd(assertValue(img.attr(attrName)), this.readPath)
    )
  }
  private resourceRenamer(node: Dom, sel: string, attrName: string) {
    const allResources = new Map(
      this.parsed.resources.map((r) => [r.readPath, r])
    )
    node.forEach(sel, (node) => {
      const resPath = this.toAbsolute(assertValue(node.attr(attrName)))
      const resource = assertValue(
        allResources.get(resPath),
        `BUG: Could not find resource in the set of resources that were parsed: '${resPath}'`
      )
      node.attr(attrName, this.relativeToMe(resource.newPath))
    })
  }
  protected async convert(): Promise<Node> {
    const doc = dom(await this.readXml())
    // Rename the resources
    RESOURCE_SELECTORS.forEach(([sel, attrName]) =>
      this.resourceRenamer(doc, sel, attrName)
    )

    const headingFixerFactory = (topHeaderValue = 1) => {
      const stack: { original: number; mapped: number }[] = []

      return (el: Dom) => {
        const originalDepth = parseInt(el.tagName.slice(-1), 10)
        assertTrue(!isNaN(originalDepth), `Invalid heading tag: ${el.tagName}`)

        while (
          stack.length > 0 &&
          stack[stack.length - 1].original >= originalDepth
        ) {
          stack.pop()
        }

        const parent = stack[stack.length - 1]
        const idealDepth = Math.max(1, originalDepth)
        const targetDepth = parent
          ? Math.min(idealDepth, parent.mapped + 1) // Prevents skipping levels while preserving valid depths
          : topHeaderValue
        stack.push({ original: originalDepth, mapped: targetDepth })

        if (targetDepth !== originalDepth) {
          el.replaceWith(
            doc.create(
              `h:h${targetDepth}`,
              el.attrs,
              el.children,
              getPos(el.node)
            )
          )
        }
      }
    }

    if (this.ancestorTitle != null) {
      const newTitleNode = doc.create(
        'h:h1',
        { 'data-type': 'document-title' },
        [this.ancestorTitle.title],
        this.ancestorTitle.pos
      )
      const content = doc.findOne('//h:div[@data-type]')
      content.children = [newTitleNode, ...content.children]
    }

    doc.forEach(
      '//h:h1 | //h:h2 | //h:h3 | //h:h4 | //h:h5 | //h:h6',
      headingFixerFactory()
    )

    // Add a CSS file
    doc.findOne('//h:head').children = [
      <h:title>{this.parsed.title}</h:title>,
      <h:link rel="stylesheet" type="text/css" href="the-style-epub.css" />,
    ]

    // Re-namespace the MathML elements
    doc.forEach('//h:math|//h:math//*', (el) => {
      el.replaceWith(
        doc.create(`m:${el.tagName}`, el.attrs, el.children, getPos(el.node))
      )
    })

    // Remove annotation-xml elements because the validator requires an optional "name" attribute
    // This element is added by https://github.com/openstax/cnx-transforms/blob/85cd5edd5209fcb4c4d72698836a10e084b9ba00/cnxtransforms/xsl/content2presentation-files/cnxmathmlc2p.xsl#L49
    doc.forEach('//m:math//m:annotation-xml|//h:math//h:annotation-xml', (n) =>
      n.remove()
    )

    const attrsToRemove = ['itemprop', 'valign', 'group-by', 'use-subtitle']
    attrsToRemove.forEach((attrName) =>
      doc.forEach(`//*[@${attrName}]`, (el) => el.attr(attrName, null))
    )

    doc.forEach('//h:script|//h:style', (n) => n.remove())

    // Delete all iframes
    doc.forEach('//h:iframe', (n) => n.remove())

    // Fix links to other Pages
    const allPages = new Map(this.parsed.pageLinks.map((r) => [r.readPath, r]))
    doc.forEach(pageLinkXpath, (a) => {
      const u = new URL(
        assertValue(a.attr('href')),
        'https://example-i-am-not-really-used.com'
      )
      const pagePathRel = u.pathname.slice(1) // remove leading slash
      const hash = u.hash.slice(1) // skip the first character because it is '#'

      const targetPath = this.toAbsolute(pagePathRel)
      const targetPage = assertValue(
        allPages.get(targetPath),
        `BUG: Could not find the target page in the set of pages that were parsed: source='${this.readPath}' target='${targetPath}'`
      )

      const newTargetPath = this.relativeToMe(targetPage.newPath)
      const newHref = hash ? `${newTargetPath}#${hash}` : newTargetPath
      a.attr('href', newHref)
    })

    // Mark the first page of chapters and units for screen readers
    if (this.ariaSpec !== null) {
      const content = doc.findOne('//h:div[@data-type]')
      const epubType = assertValue(
        EPUB_TYPE_BY_ARIA_ROLE[this.ariaSpec.role],
        `BUG: No epub:type mapped for ARIA role '${this.ariaSpec.role}'`
      )
      content.attr('role', this.ariaSpec.role)
      content.attr('epub:type', epubType)
      content.attr('aria-label', this.ariaSpec.label ?? this.parsed.title)
    }

    return doc.node
  }
}
