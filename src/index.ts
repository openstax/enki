import { resolve, relative, join, dirname } from 'path'
import { Factory, Opt } from './factory'
import { assertValue, readXmlWithSourcemap, selectAll, selectOne, writeXmlWithSourcemap, XmlFormat, NAMESPACES } from './utils'

class Factorio {
    public readonly pages = new Factory(absPath => new XHTMLPageFile(this, absPath), resolve)
    public readonly tocs = new Factory(absPath => new XHTMLTocFile(this, absPath), resolve)
    public readonly resources = new Factory(absPath => new ResourceFile(this, absPath), resolve)
}

abstract class File {
    private _newPath: Opt<string>
    constructor(protected readonly factorio: Factorio, protected readonly absPath: string) { }
    rename(relPath: string, relTo: Opt<string>) {
        this._newPath = relTo === undefined ? relPath : join(dirname(relTo), relPath)
    }
    public newPath() {
        return this._newPath || this.absPath
    }
}

class ResourceFile extends File { }

const RESOURCE_SELECTORS: Array<[string, string]> = [
    [ '//h:img', 'src'],
    [ '//h:a[starts-with(@href, "../resources/")]', 'href'],
    [ '//h:object', 'data'],
    [ '//h:embed', 'src'],
]

type PropsAndResources = {
    hasMathML: boolean
    hasRemoteResources: boolean
    hasScripts: boolean
    resources: ResourceFile[]
}
class XHTMLPageFile extends File {
    async parse(): Promise<PropsAndResources> {
        const doc = await readXmlWithSourcemap(this.absPath)
        const resources = RESOURCE_SELECTORS.map(([sel, attrName]) => this.resourceFinder(doc, sel, attrName)).flat()
        return {
            hasMathML: selectAll('//m:math', doc).length > 0,
            hasRemoteResources: selectAll('//h:iframe|//h:object/h:embed', doc).length > 0,
            hasScripts: selectAll('//h:script', doc).length > 0,
            resources
        }
    }
    private resourceFinder(node: Node, sel: string, attrName: string) {
        return selectAll<Element>(sel, node).map(img => this.factorio.resources.getOrAdd(assertValue(img.getAttribute(attrName)), this.absPath))
    }
    private resourceRenamer(node: Node, sel: string, attrName: string) {
        const resources = selectAll<Element>(sel, node)
        for (const node of resources) {
            const resource = this.factorio.resources.getOrAdd(assertValue(node.getAttribute(attrName)), this.absPath)
            node.setAttribute(attrName, relative(dirname(this.absPath), resource.newPath()))
        }
    }
    async write() {
        const doc = await readXmlWithSourcemap(this.absPath)
        // Rename the resources
        RESOURCE_SELECTORS.forEach(([sel, attrName]) => this.resourceRenamer(doc, sel, attrName))
        
        // Add a CSS file
        const head = selectOne<Element>('//h:head', doc)
        const cssEl = doc.createElementNS(NAMESPACES.h, 'link')
        cssEl.setAttribute('rel', 'stylesheet')
        cssEl.setAttribute('type', 'text/css')
        cssEl.setAttribute('href', 'the-style-epub.css')
        head.appendChild(cssEl)

        // Re-namespace the MathML elements
        const mathEls = selectAll<Element>('//h:math|//h:math//*', doc)
        function helper(doc: Document, el: Element, newNamespace: string) {
            const newEl = doc.createElementNS(newNamespace, el.tagName)
            for (const attr of Array.from(el.attributes)) {
                newEl.setAttribute(attr.name, attr.value)
            }
            for (const child of Array.from(el.childNodes)) {
                newEl.appendChild(child)
            }
            el.parentNode?.replaceChild(newEl, el)
        }
        mathEls.forEach(el => helper(doc, el, NAMESPACES.m))

        // Remove annotation-xml elements because the validator requires an optional "name" attribute
        // This element is added by https://github.com/openstax/cnx-transforms/blob/85cd5edd5209fcb4c4d72698836a10e084b9ba00/cnxtransforms/xsl/content2presentation-files/cnxmathmlc2p.xsl#L49
        removeElements(doc, '//m:math//m:annotation-xml|//h:math//h:annotation-xml')

        const attrsToRemove = [
            'itemprop',
            'valign',
            'group-by',
            'use-subtitle'
        ]
        attrsToRemove.forEach(attrName => selectAll<Element>(`//*[@${attrName}]`, doc).forEach(el => el.removeAttribute(attrName)))
        
        removeElements(doc, '//h:script|//h:style')

        writeXmlWithSourcemap(this.newPath(), doc, XmlFormat.XHTML5)
    }
}

function removeElements(doc: Node, sel: string) {
    selectAll<Element>(sel, doc).forEach(el => el.parentNode?.removeChild(el))
}

enum TocTreeType {
    INNER = 'INNER',
    LEAF = 'LEAF'
}
type TocTree = {
    type: TocTreeType.INNER
    title: string
    children: TocTree[]
} | {
    type: TocTreeType.LEAF
    title: string
    page: XHTMLPageFile
}
class XHTMLTocFile extends File {
    async parse(): Promise<TocTree[]> {
        const doc = await readXmlWithSourcemap(this.absPath)
        const tree = selectAll<Element>('//h:nav/h:ol/h:li', doc).map(el => this.buildChildren(el))
        return tree
    }
    private buildChildren(li: Element): TocTree {
        // 3 options are: Subbook node, Page leaf, subbook leaf (only CNX)
        const children = selectAll<Element>('h:ol/h:li', li)
        if (children.length > 0) {
            return {
                type: TocTreeType.INNER,
                title: this.selectText('h:a/h:span/text()', li), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                children: children.map(c => this.buildChildren(c))
            }
        } else if (selectAll('h:a[not(starts-with(@href, "#"))]', li).length > 0) {
            const href = assertValue(selectOne<Element>('h:a[not(starts-with(@href, "#"))]', li).getAttribute('href'))
            return {
                type: TocTreeType.LEAF,
                title: this.selectText('h:a/h:span/text()', li), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                page: this.factorio.pages.getOrAdd(href, this.absPath)
            }
        } else {
            throw new Error('BUG: non-page leaves are not supported yet')
        }
    }
    private selectText(sel: string, node: Node) {
        return selectAll<Text>(sel, node).map(t => t.textContent).join('')
    }
}

async function fn() {

    const factorio = new Factorio()

    const toc = factorio.tocs.getOrAdd('../test.xhtml', __filename)
    const tocInfo = await toc.parse()
    console.log(tocInfo)

    const first = tocInfo[0]
    if (first.type === TocTreeType.LEAF) {
        const pageInfo = await first.page.parse()
        console.log(pageInfo)
        // {
        //   hasMathML: true,
        //   hasRemoteResources: true,
        //   hasScripts: true,
        //   resources: [
        //     ResourceFile {
        //       absPath: '/home/...path-to.../enki/resources/foo.jpg'
        //     }
        //   ]
        // }

        first.page.rename('../test-out.xhtml', __filename)
        pageInfo.resources[0].rename('../foo/bar.jpg', first.page.newPath())
        await first.page.write()
    } else { throw new Error('BUG: expected first child in Toc to be a Page') }
}

fn().catch(err => console.error(err))