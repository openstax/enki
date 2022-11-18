import { resolve, relative, join, dirname } from 'path'
import * as sourceMapSupport from 'source-map-support';
import { Factory, Opt } from './factory'
import { $, $$, $$node, Dom, dom } from './minidom'
import { assertValue, readXmlWithSourcemap, writeXmlWithSourcemap, XmlFormat } from './utils'

sourceMapSupport.install()

class Factorio {
    public readonly pages = new Factory(absPath => new XHTMLPageFile(this, absPath), resolve)
    public readonly tocs = new Factory(absPath => new XHTMLTocFile(this, absPath), resolve)
    public readonly resources = new Factory(absPath => new ResourceFile(this, absPath), resolve)
}

abstract class File {
    private _newPath: Opt<string>
    constructor(protected readonly factorio: Factorio, public readonly absPath: string) { }
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
            hasMathML: $$('//m:math', doc).length > 0,
            hasRemoteResources: $$('//h:iframe|//h:object/h:embed', doc).length > 0,
            hasScripts: $$('//h:script', doc).length > 0,
            resources
        }
    }
    private resourceFinder(node: Node, sel: string, attrName: string) {
        return $$(sel, node).map(img => this.factorio.resources.getOrAdd(assertValue(img.attr(attrName)), this.absPath))
    }
    private resourceRenamer(node: Node, sel: string, attrName: string) {
        const resources = $$(sel, node)
        for (const node of resources) {
            const resource = this.factorio.resources.getOrAdd(assertValue(node.attr(attrName)), this.absPath)
            node.attr(attrName, relative(dirname(this.absPath), resource.newPath()))
        }
    }
    async write() {
        const doc = await readXmlWithSourcemap(this.absPath)
        // Rename the resources
        RESOURCE_SELECTORS.forEach(([sel, attrName]) => this.resourceRenamer(doc, sel, attrName))
        
        // Add a CSS file
        $('//h:head', doc).children = [
            dom(doc, 'h:link', {
                rel: 'stylesheet',
                type: 'text/css',
                href: 'the-style-epub.css'
            })
        ]

        // Re-namespace the MathML elements
        const mathEls = $$('//h:math|//h:math//*', doc)
        mathEls.forEach(el => {
            el.replaceWith(dom(doc, `m:${el.tagName}`, el.attrs, el.children))
        })


        // Remove annotation-xml elements because the validator requires an optional "name" attribute
        // This element is added by https://github.com/openstax/cnx-transforms/blob/85cd5edd5209fcb4c4d72698836a10e084b9ba00/cnxtransforms/xsl/content2presentation-files/cnxmathmlc2p.xsl#L49
        $$('//m:math//m:annotation-xml|//h:math//h:annotation-xml', doc).forEach(n => n.remove())

        const attrsToRemove = [
            'itemprop',
            'valign',
            'group-by',
            'use-subtitle'
        ]
        attrsToRemove.forEach(attrName => $$(`//*[@${attrName}]`, doc).forEach(el => el.attr(attrName, null)))
        
        $$('//h:script|//h:style', doc).forEach(n => n.remove())

        writeXmlWithSourcemap(this.newPath(), doc, XmlFormat.XHTML5)
    }
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
        const tree = $$('//h:nav/h:ol/h:li', doc).map(el => this.buildChildren(el))
        return tree
    }
    private buildChildren(li: Dom, acc?: XHTMLPageFile[]): TocTree {
        // 3 options are: Subbook node, Page leaf, subbook leaf (only CNX)
        const children = $$('h:ol/h:li', li)
        if (children.length > 0) {
            return {
                type: TocTreeType.INNER,
                title: this.selectText('h:a/h:span/text()', li), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                children: children.map(c => this.buildChildren(c, acc))
            }
        } else if ($$('h:a[not(starts-with(@href, "#"))]', li).length > 0) {
            const href = assertValue($('h:a[not(starts-with(@href, "#"))]', li).attr('href'))
            const page = this.factorio.pages.getOrAdd(href, this.absPath)
            acc?.push(page)
            return {
                type: TocTreeType.LEAF,
                title: this.selectText('h:a/h:span/text()', li), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                page
            }
        } else {
            throw new Error('BUG: non-page leaves are not supported yet')
        }
    }
    /** HACK: Lazy... Maybe jsut flatten the ToC in the future */
    async getPages() {
        const doc = await readXmlWithSourcemap(this.absPath)
        const ret: XHTMLPageFile[] = []
        $$('//h:nav/h:ol/h:li', doc).forEach(el => this.buildChildren(el, ret))
        return ret
    }
    private selectText(sel: string, node: Dom) {
        return $$node<Text>(sel, node).map(t => t.textContent).join('')
    }
    async write() {
        const doc = await readXmlWithSourcemap(this.absPath)

        // Remove ToC entries that have non-Page leaves
        $$('//h:nav//h:li[not(.//h:a)]', doc).forEach(e => e.remove())

        // Unwrap chapter links and combine titles into a single span
        $$('h:a[starts-with(@href, "#")]', doc).forEach(el => {
            const children = $$('h:span/node()', el)
            el.replaceWith(dom(doc, 'h:span', {}, children))
        })

        $$('h:a[not(starts-with(@href, "#")) and h:span]', doc).forEach(el => {
            const children = $$('h:span/node()', doc)
            el.children = [
                dom(doc, 'h:span', {}, children)
            ]
        })
        
        // Rename the hrefs to XHTML files to their new name
        $$('//*[@href]', doc).forEach(el => {
            const page = this.factorio.pages.getOrAdd(assertValue(el.attr('href')), this.absPath)
            el.attr('href', relative(dirname(this.absPath), page.newPath()))
        })
    
        // Remove extra attributes
        const attrsToRemove = [
            'cnx-archive-shortid',
            'cnx-archive-uri',
            'itemprop',
        ]
        attrsToRemove.forEach(attrName => $$(`//*[@${attrName}]`, doc).forEach(el => el.attr(attrName, null)))
        
        // Add the epub:type="nav" attribute
        $('//h:nav', doc).attr('epub:type', 'toc')

        writeXmlWithSourcemap(this.newPath(), doc, XmlFormat.XHTML5)
    }
}

async function fn() {

    const factorio = new Factorio()

    const toc = factorio.tocs.getOrAdd('../test-toc.xhtml', __filename)
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

        // first.page.rename('../test-out.xhtml', __filename)
        pageInfo.resources[0].rename('../foo/bar.jpg', first.page.newPath())
        // await first.page.write()
    } else { throw new Error('BUG: expected first child in Toc to be a Page') }


    let allPages: XHTMLPageFile[] = []
    const tocFiles = Array.from(factorio.tocs.all)
    for (const tocFile of tocFiles) {
        const pages = await tocFile.getPages()
        allPages = [...allPages, ...pages]
    }

    allPages.forEach(p => p.rename(p.absPath.replace(':', '%3A'), undefined))
    
    
    tocFiles.forEach(p => p.rename(`${p.absPath}-out.xhtml`, undefined))

    for (const page of allPages) {
        await page.write()
    }
    for (const tocFile of tocFiles) {
        await tocFile.write()
    }
}

fn().catch(err => console.error(err))