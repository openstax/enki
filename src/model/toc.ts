import { readFileSync } from 'fs';
import { relative, dirname, basename } from 'path'
import { $, $$, $$node, Dom, dom } from '../minidom'
import { assertValue, parseXml, readXmlWithSourcemap, writeXmlWithSourcemap, XmlFormat } from '../utils'
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
export class TocFile extends XMLFile {
    async parse(): Promise<TocTree[]> {
        const doc = await readXmlWithSourcemap(this.origPath)
        const tree = $$('//h:nav/h:ol/h:li', doc).map(el => this.buildChildren(el))
        return tree
    }
    private buildChildren(li: Dom, acc?: PageFile[]): TocTree {
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
            const page = this.factorio.pages.getOrAdd(href, this.origPath)
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
    protected getPagesFromDoc(doc: Document) {
        const ret: PageFile[] = []
        $$('//h:nav/h:ol/h:li', doc).forEach(el => this.buildChildren(el, ret))
        return ret
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
        const metadataFile = this.origPath.replace('.toc.xhtml', '.toc-metadata.json')
        const json = JSON.parse(readFileSync(metadataFile, 'utf-8'))
        return {
            title: json.title as string,
            revised: json.revised as string,
            slug: json.slug as string,
            licenseUrl: json.license.url as string,
            language: json.language as string,
        }
    }
    
    private selectText(sel: string, node: Dom) {
        return $$node<Text>(sel, node).map(t => t.textContent).join('')
    }
    protected transform(doc: Document) {
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
            const page = this.factorio.pages.getOrAdd(assertValue(el.attr('href')), this.origPath)
            el.attr('href', this.relativeToMe(page.newPath()))
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
    }

    public async writeOPFFile(destPath: string) {
        const inDoc = await readXmlWithSourcemap(this.origPath)
        const doc = parseXml('<package xmlns="http://www.idpf.org/2007/opf"/>', '_unused......')
        const pkg = $('opf:package', doc)
        pkg.attrs = {version: '3.0', 'unique-identifier': 'uid'}
    
        const allPages = new Set<PageFile>()
        const allResources: Set<ResourceFile> = new Set()
        
        // keep looking through XHTML file links and add those to the set of allPages
        async function recPages(allPages: Set<PageFile>, allResources: Set<ResourceFile>, page: PageFile) {
            if (allPages.has(page)) return
            const p = await page.parse()
            for (const r of p.resources) { allResources.add(r) }
            for (const c of p.pageLinks) {
                await recPages(allPages, allResources, c)
            }
        }
        for (const page of this.getPagesFromDoc(inDoc)) {
            recPages(allPages, allResources, page)
        }

        const bookItems: Dom[] = []
        for (const page of allPages) {
            const p = await page.parse()
            const props: string[] = []
            if (p.hasMathML) props.push('mathml')
            if (p.hasRemoteResources) props.push('remote-resources')
            if (p.hasScripts) props.push('scripted')

            bookItems.push(dom(doc, 'opf:item', {
                'media-type': 'application/xhtml+xml', 
                id: `idxhtml_${basename(page.newPath())}`, 
                properties: props.join(' '), 
                href: relative(dirname(destPath), page.newPath())}),)
            
            for(const r of p.resources) {
                allResources.add(r)
            }
        }

        let i = 0
        for (const resource of allResources) {
            const {mimeType, originalExtension} = await resource.parse()

            let newExtension = (mimetypeExtensions)[mimeType] || originalExtension
            resource.rename(`${resource.newPath()}.${newExtension}`, undefined)

            bookItems.push(dom(doc, 'opf:item', {
                'media-type': mimeType, 
                id: `idresource_${i}`, 
                href: relative(dirname(destPath), resource.newPath())}),)
            i++
        }

        
        const bookMetadata = await this.parseMetadata()
        // Remove the timezone from the revised_date
        const revised = bookMetadata.revised.replace('+00:00', 'Z')
    
    
        pkg.children = [ dom(doc, 'opf:metadata', {}, [
            dom(doc, 'dc:title', {}, [ bookMetadata.title ]),
            dom(doc, 'dc:language', {}, [bookMetadata.language]),
            dom(doc, 'opf:meta', {property: 'dcterms:modified'}, [ revised]),
            dom(doc, 'opf:meta', {property: 'dcterms:license'}, [ bookMetadata.licenseUrl]),
            // dom(doc, 'opf:meta', {property: 'dcterms:alternative'}, [ 'col11992']),
            dom(doc, 'dc:identifier', {id: 'uid'}, [`dummy-openstax.org-id.${bookMetadata.slug}`]),
            dom(doc, 'dc:creator', {}, ['Is it OpenStax???']),
        ]), dom(doc, 'opf:manifest', {}, [
            dom(doc, 'opf:item', {id: 'just-the-book-style', href: 'the-style-epub.css', 'media-type': "text/css"}),
            dom(doc, 'opf:item', {id: 'nav', properties: 'nav', 'media-type': 'application/xhtml+xml', href: relative(dirname(destPath), this.newPath())}),
            ...bookItems
        ])]
    
        writeXmlWithSourcemap(destPath, doc, XmlFormat.XHTML5)
    }

}
