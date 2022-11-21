import { $, $$, dom } from '../minidom'
import { assertValue, readXmlWithSourcemap } from '../utils'
import { ResourceFile, XMLFile } from './file'

const RESOURCE_SELECTORS: Array<[string, string]> = [
    [ '//h:img', 'src'],
    [ '//h:a[starts-with(@href, "../resources/")]', 'href'],
    [ '//h:object', 'data'],
    [ '//h:embed', 'src'],
]

export type PageData = {
    hasMathML: boolean
    hasRemoteResources: boolean
    hasScripts: boolean
    pageLinks: PageFile[]
    resources: ResourceFile[]
}
export class PageFile extends XMLFile<PageData> {
    protected async innerParse() {
        const doc = await readXmlWithSourcemap(this.readPath)
        const pageLinks = $$('//h:a[not(starts-with(@href, "http:") or starts-with(@href, "https:") or starts-with(@href, "#"))]', doc).map(a => {
            const u = new URL(assertValue(a.attr('href')), 'https://example-i-am-not-really-used.com')
            return this.factorio.pages.getOrAdd(u.pathname, this.readPath)
        })
        const resources = RESOURCE_SELECTORS.map(([sel, attrName]) => this.resourceFinder(doc, sel, attrName)).flat()
        return {
            hasMathML: $$('//m:math', doc).length > 0,
            hasRemoteResources: $$('//h:iframe|//h:object/h:embed', doc).length > 0,
            hasScripts: $$('//h:script', doc).length > 0,
            pageLinks,
            resources
        }
    }
    private resourceFinder(node: Node, sel: string, attrName: string) {
        return $$(sel, node).map(img => this.factorio.resources.getOrAdd(assertValue(img.attr(attrName)), this.readPath))
    }
    private resourceRenamer(node: Node, sel: string, attrName: string) {
        const resources = $$(sel, node)
        for (const node of resources) {
            const resource = this.factorio.resources.getOrAdd(assertValue(node.attr(attrName)), this.readPath)
            node.attr(attrName, this.relativeToMe(resource.newPath))
        }
    }
    protected transform(doc: Document) {
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
    }
}
