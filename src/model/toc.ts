import { relative, dirname, basename } from 'path'
import { Dom, dom } from '../minidom'
import { assertValue, parseXml, readXmlWithSourcemap, XmlFormat } from '../utils'
import type { Factory } from './factory';
import { ResourceFile, XMLFile } from './file';
import type { PageFile } from './page';

const mimetypeExtensions: {[k: string]: string} = {
    'image/jpeg':         'jpeg',
    'image/png':          'png',
    'image/gif':          'gif',
    'image/tiff':         'tiff',
    'image/svg+xml':      'svg',
    'audio/mpeg':         'mpg',
    'audio/basic':        'au',
    'application/pdf':    'pdf',
    'application/zip':    'zip',
    'audio/midi':         'midi',
    'audio/x-wav':        'wav',
    // 'text/plain':         'txt',
    'application/x-shockwave-flash': 'swf',
    // 'application/octet-stream':
}
export enum TocTreeType {
    INNER = 'INNER',
    LEAF = 'LEAF'
}
export type TocTree = {
    type: TocTreeType.INNER
    title: string
    children: TocTree[]
} | {
    type: TocTreeType.LEAF
    title: string
    page: PageFile
}
type TocData = {
    toc: TocTree[]
    allPages: Set<PageFile>
    allResources: Set<ResourceFile>
}
export class TocFile extends XMLFile<TocData> {
    protected async innerParse(pageFactory: Factory<PageFile>, resourceFactory: Factory<ResourceFile>) {
        const doc = dom(await readXmlWithSourcemap(this.readPath))
        const toc = doc.map('//h:nav/h:ol/h:li', el => this.buildChildren(pageFactory, el))

        const allPages = new Set<PageFile>()
        const allResources = new Set<ResourceFile>()

        // keep looking through XHTML file links and add those to the set of allPages
        async function recPages(page: PageFile) {
            if (allPages.has(page)) return
            await page.parse(pageFactory, resourceFactory)
            allPages.add(page)
            const p = page.data
            for (const r of p.resources) { await r.parse(pageFactory, resourceFactory); allResources.add(r) }
            for (const c of p.pageLinks) {
                await recPages(c)
            }
        }
        const tocPages: PageFile[] = []
        doc.forEach('//h:nav/h:ol/h:li', el => this.buildChildren(pageFactory, el, tocPages))

        for (const page of tocPages) {
            await recPages(page)
        }
        
        return {
            toc, allPages, allResources
        }
    }
    private buildChildren(pageFactory: Factory<PageFile>, li: Dom, acc?: PageFile[]): TocTree {
        // 3 options are: Subbook node, Page leaf, subbook leaf (only CNX)
        const children = li.find('h:ol/h:li')
        if (children.length > 0) {
            return {
                type: TocTreeType.INNER,
                title: this.selectText('h:a/h:span/text()', li), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                children: children.map(c => this.buildChildren(pageFactory, c, acc))
            }
        } else if (li.has('h:a[not(starts-with(@href, "#"))]')) {
            const href = assertValue(li.findOne('h:a[not(starts-with(@href, "#"))]').attr('href'))
            const page = pageFactory.getOrAdd(href, this.readPath)
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
    public getPagesFromToc(toc: TocTree, acc: PageFile[] = []) {
        if (toc.type === TocTreeType.LEAF) {
            acc?.push(toc.page)
        } else {
            toc.children.forEach(c => this.getPagesFromToc(c, acc))
        }
        return acc
    }
    async parseMetadata() {
        const metadataFile = this.readPath.replace('.toc.xhtml', '.toc-metadata.json')
        const json = this.readJson<any>(metadataFile)
        return {
            title: json.title as string,
            revised: json.revised as string,
            slug: json.slug as string,
            licenseUrl: json.license.url as string,
            language: json.language as string,
        }
    }
    
    private selectText(sel: string, node: Dom) {
        return node.findNodes<Text>(sel).map(t => t.textContent).join('')
    }
    protected transform(doc: Dom) {
        const allPages = new Map(Array.from(this.data.allPages).map(r => ([r.readPath, r])))
        // Remove ToC entries that have non-Page leaves
        doc.forEach('//h:nav//h:li[not(.//h:a)]', e => e.remove())

        // Unwrap chapter links and combine titles into a single span
        doc.forEach('h:a[starts-with(@href, "#")]', el => {
            const children = el.find('h:span/node()')
            el.replaceWith(doc.create('h:span', {}, children))
        })

        doc.forEach('h:a[not(starts-with(@href, "#")) and h:span]', el => {
            const children = doc.find('h:span/node()')
            el.children = [
                doc.create('h:span', {}, children)
            ]
        })
        
        // Rename the hrefs to XHTML files to their new name
        doc.forEach('//*[@href]', el => {
            const page = assertValue(allPages.get(this.toAbsolute(assertValue(el.attr('href')))))
            el.attr('href', this.relativeToMe(page.newPath))
        })
    
        // Remove extra attributes
        const attrsToRemove = [
            'cnx-archive-shortid',
            'cnx-archive-uri',
            'itemprop',
        ]
        attrsToRemove.forEach(attrName => doc.forEach(`//*[@${attrName}]`, el => el.attr(attrName, null)))
        
        // Add the epub:type="nav" attribute
        doc.findOne('//h:nav').attr('epub:type', 'toc')
    }

    public async writeOPFFile(destPath: string) {
        const d = parseXml('<package xmlns="http://www.idpf.org/2007/opf"/>', '_unused......')
        const doc = dom(d)
        const pkg = doc.findOne('opf:package')
        pkg.attrs = {version: '3.0', 'unique-identifier': 'uid'}
    
        const { allPages, allResources} = this.data
        
        const bookItems: Dom[] = []
        for (const page of allPages) {
            const p = page.data
            const props: string[] = []
            if (p.hasMathML) props.push('mathml')
            if (p.hasRemoteResources) props.push('remote-resources')
            if (p.hasScripts) props.push('scripted')

            bookItems.push(doc.create('opf:item', {
                'media-type': 'application/xhtml+xml', 
                id: `idxhtml_${basename(page.newPath)}`, 
                properties: props.join(' '), 
                href: relative(dirname(destPath), page.newPath)}),)
            
            for(const r of p.resources) {
                allResources.add(r)
            }
        }

        let i = 0
        for (const resource of allResources) {
            const {mimeType, originalExtension} = resource.data

            let newExtension = (mimetypeExtensions)[mimeType] || originalExtension
            resource.rename(`${resource.newPath}.${newExtension}`, undefined)

            bookItems.push(doc.create('opf:item', {
                'media-type': mimeType, 
                id: `idresource_${i}`, 
                href: relative(dirname(destPath), resource.newPath)}),)
            i++
        }

        
        const bookMetadata = await this.parseMetadata()
        // Remove the timezone from the revised_date
        const revised = bookMetadata.revised.replace('+00:00', 'Z')
    
    
        pkg.children = [ doc.create('opf:metadata', {}, [
            doc.create('dc:title', {}, [ bookMetadata.title ]),
            doc.create('dc:language', {}, [bookMetadata.language]),
            doc.create('opf:meta', {property: 'dcterms:modified'}, [ revised]),
            doc.create('opf:meta', {property: 'dcterms:license'}, [ bookMetadata.licenseUrl]),
            // doc.create('opf:meta', {property: 'dcterms:alternative'}, [ 'col11992']),
            doc.create('dc:identifier', {id: 'uid'}, [`dummy-openstax.org-id.${bookMetadata.slug}`]),
            doc.create('dc:creator', {}, ['Is it OpenStax???']),
        ]), doc.create('opf:manifest', {}, [
            doc.create('opf:item', {id: 'just-the-book-style', href: 'the-style-epub.css', 'media-type': "text/css"}),
            doc.create('opf:item', {id: 'nav', properties: 'nav', 'media-type': 'application/xhtml+xml', href: relative(dirname(destPath), this.newPath)}),
            ...bookItems
        ])]
    
        this.writeXml(destPath, d, XmlFormat.XHTML5)
    }

}
