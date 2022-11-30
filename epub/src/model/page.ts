import { Dom, dom } from '../minidom'
import { assertValue } from '../utils'
import type { Factorio } from './factorio'
import type { Factory } from './factory'
import { ResourceFile, XmlFile } from './file'

const RESOURCE_SELECTORS: Array<[string, string]> = [
    ['//h:img', 'src'],
    ['//h:a[starts-with(@href, "../resources/")]', 'href'],
    ['//h:object', 'data'],
    ['//h:embed', 'src'],
]

export type PageData = {
    hasMathML: boolean
    hasRemoteResources: boolean
    pageLinks: PageFile[]
    resources: ResourceFile[]
}

export class PageFile extends XmlFile<PageData> {
    async parse(factorio: Factorio): Promise<void> {
        const doc = dom(await this.readXml(this.readPath))
        const pageLinks = doc.map('//h:a[not(starts-with(@href, "http:") or starts-with(@href, "https:") or starts-with(@href, "#"))]', a => {
            const u = new URL(assertValue(a.attr('href')), 'https://example-i-am-not-really-used.com')
            return factorio.pages.getOrAdd(u.pathname, this.readPath)
        })
        const resources = RESOURCE_SELECTORS.map(([sel, attrName]) => this.resourceFinder(factorio.resources, doc, sel, attrName)).flat()
        this.data = {
            hasMathML: doc.has('//m:math|//h:math'),
            hasRemoteResources: doc.has('//h:iframe|//h:object/h:embed'),
            pageLinks,
            resources
        }
    }
    private resourceFinder(resourceFactory: Factory<ResourceFile>, node: Dom, sel: string, attrName: string) {
        return node.map(sel, img => resourceFactory.getOrAdd(assertValue(img.attr(attrName)), this.readPath))
    }
    private resourceRenamer(node: Dom, sel: string, attrName: string) {
        const allResources = new Map(this.data.resources.map(r => ([r.readPath, r])))
        const resources = node.find(sel)
        for (const node of resources) {
            const resPath = this.toAbsolute(assertValue(node.attr(attrName)))
            const resource = assertValue(allResources.get(resPath), `BUG: Could not find resource in the set of resources that were parsed: '${resPath}'`)
            node.attr(attrName, this.relativeToMe(resource.newPath))
        }
    }
    protected async convert(): Promise<Node> {
        const doc = dom(await this.readXml())
        // Rename the resources
        RESOURCE_SELECTORS.forEach(([sel, attrName]) => this.resourceRenamer(doc, sel, attrName))

        // Add a CSS file
        doc.findOne('//h:head').children = [
            doc.create('h:link', {
                rel: 'stylesheet',
                type: 'text/css',
                href: 'the-style-epub.css'
            })
        ]

        // Re-namespace the MathML elements
        doc.forEach('//h:math|//h:math//*', el => {
            el.replaceWith(doc.create(`m:${el.tagName}`, el.attrs, el.children))
        })

        // Remove annotation-xml elements because the validator requires an optional "name" attribute
        // This element is added by https://github.com/openstax/cnx-transforms/blob/85cd5edd5209fcb4c4d72698836a10e084b9ba00/cnxtransforms/xsl/content2presentation-files/cnxmathmlc2p.xsl#L49
        doc.forEach('//m:math//m:annotation-xml|//h:math//h:annotation-xml', n => n.remove())

        const attrsToRemove = [
            'itemprop',
            'valign',
            'group-by',
            'use-subtitle'
        ]
        attrsToRemove.forEach(attrName => doc.forEach(`//*[@${attrName}]`, el => el.attr(attrName, null)))

        doc.forEach('//h:script|//h:style', n => n.remove())
        return doc.node
    }
}
