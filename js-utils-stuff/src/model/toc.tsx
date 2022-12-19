import { basename,resolve,dirname ,sep} from 'path'
import { dom, Dom, fromJSX, JSXNode } from '../minidom'
import { assertValue, getPos, Pos } from '../utils'
import type { Factorio } from './factorio';
import type { Factory, Opt } from './factory';
import { ResourceFile, XmlFile } from './file';
import type { PageFile } from './page';

export enum TocTreeType {
    INNER = 'INNER',
    LEAF = 'LEAF'
}
export type TocTree = {
    type: TocTreeType.INNER
    title: string
    titlePos: Pos
    children: TocTree[]
} | {
    type: TocTreeType.LEAF
    title: string
    titlePos: Pos
    page: PageFile
    pagePos: Pos
}
type TocData = {
    toc: TocTree[]
    allPages: Set<PageFile>
    allResources: Set<ResourceFile>
    
    // From the metadata.json file
    title: string
    revised: string
    slug: string
    licenseUrl: string
    language: string
    authors: string
}

export class TocFile extends XmlFile<TocData> {
    async parse(factorio: Factorio): Promise<void> {
        if (this._parsed !== undefined) return // Only parse once
        const metadataFile = this.readPath.replace('.toc.xhtml', '.toc-metadata.json')
        const doc = dom(await this.readXml())
        const metadata = await this.readJson<any>(metadataFile)
        const title = metadata.title as string
        const revised = metadata.revised as string
        const slug = metadata.slug as string
        const licenseUrl = metadata.license.url as string
        const language = metadata.language as string

        const collectionXml = dom(await this.readXml([resolve(dirname(this.readPath),'..'),'_attic','IO_FETCHED','collections',`${slug}.collection.xml`].join(sep)))
        const authors = collectionXml.has("//col:collection/@authors") ? collectionXml.findOne("//col:collection").attr("authors") as string: "Is it OpenStax?" 

        const tocPages: PageFile[] = []
        const toc = doc.map('//h:nav/h:ol/h:li', el => this.buildChildren(factorio.pages, el, tocPages))

        const allPages = new Set<PageFile>()
        const allResources = new Set<ResourceFile>()

        // keep looking through XHTML file links and add those to the set of allPages
        async function recPages(page: PageFile) {
            if (allPages.has(page)) return
            await page.parse(factorio)
            allPages.add(page)
            const p = page.parsed
            for (const r of p.resources) { await r.parse(factorio); allResources.add(r) }
            for (const c of p.pageLinks) {
                await recPages(c)
            }
        }

        for (const page of tocPages) {
            await recPages(page)
        }

        this._parsed = {
            toc, 
            allPages, 
            allResources,
            title,
            revised,
            slug,
            licenseUrl,
            language,
            authors
        }
    }
    private buildChildren(pageFactory: Factory<PageFile>, li: Dom, acc?: PageFile[]): TocTree {
        // 3 options are: Subbook node, Page leaf, subbook leaf (only CNX)
        const children = li.find('h:ol/h:li')
        if (children.length > 0) {
            return {
                type: TocTreeType.INNER,
                title: li.findOne('h:a').text(), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                titlePos: getPos(li.findOne('h:a').node),
                children: children.map(c => this.buildChildren(pageFactory, c, acc))
            }
        } else if (li.has('h:a[not(starts-with(@href, "#"))]')) {
            const href = assertValue(li.findOne('h:a[not(starts-with(@href, "#"))]').attr('href'))
            const page = pageFactory.getOrAdd(href, this.readPath)
            acc?.push(page)
            return {
                type: TocTreeType.LEAF,
                title: li.findOne('h:a').text(), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
                titlePos: getPos(li.findOne('h:a').node),
                page,
                pagePos: getPos(li.node),
            }
        } else {
            throw new Error('BUG: non-page leaves are not supported yet')
        }
    }
    public findDepth(toc: TocTree):number{

        if(toc.type== TocTreeType.LEAF)
        return 1
        else 
            return 1+ Math.max(...toc.children.map(d=>{
                return this.findDepth(d);
            }))
    }

    public getPagesFromToc(toc: TocTree, acc: PageFile[] = []) {
        if (toc.type === TocTreeType.LEAF) {
            acc?.push(toc.page)
        } else {
            toc.children.forEach(c => this.getPagesFromToc(c, acc))
        }
        return acc
    }

    protected async convert(): Promise<Node> {
        const doc = dom(await this.readXml())
        
        const allPages = new Map(Array.from(this.parsed.allPages).map(r => ([r.readPath, r])))
        // Remove ToC entries that have non-Page leaves
        doc.forEach('//h:nav//h:li[not(.//h:a)]', e => e.remove())

        // Unwrap chapter links and combine titles into a single span
        doc.forEach('//h:a[starts-with(@href, "#")]', el => {
            const children = el.find('h:span//text()')
            el.replaceWith(doc.create('h:span', {}, children, getPos(el.node)))
        })

        doc.forEach('//h:a[not(starts-with(@href, "#")) and h:span]', el => {
            const children = el.find('h:span//text()')
            el.children = children
        })

        // Rename the hrefs to XHTML files to their new name
        doc.forEach('//h:a[not(starts-with(@href, "http:") or starts-with(@href, "https:") or starts-with(@href, "#"))]', el => {
            const href = assertValue(el.attr('href')).split('#')[0]
            const page = assertValue(allPages.get(this.toAbsolute(href)))
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

        return doc.node
    }
}

export class OpfFile extends TocFile {

    public readonly tocFile: TocFile
    public readonly ncxFile: NcxFile

    constructor(readPath: string) {
        super(readPath)
        this.tocFile = new TocFile(readPath)
        this.ncxFile = new NcxFile(readPath)
    }

    protected override async convert(): Promise<Node> {
        const { allPages, allResources } = this.parsed

        const manifestItems: JSXNode[] = []
        for (const page of allPages) {
            const p = page.parsed
            const props: string[] = []
            if (p.hasMathML) props.push('mathml')
            if (p.hasRemoteResources) props.push('remote-resources')

            const id = `idxhtml_${basename(page.newPath)}`
            manifestItems.push(<opf:item
                media-type='application/xhtml+xml'
                id={id}
                properties={props.length === 0 ? undefined : props.join(' ')}
                href={this.relativeToMe(page.newPath)} />)
            
            for (const r of p.resources) {
                allResources.add(r)
            }
        }

        const spineItems: JSXNode[] = []
        const pagesInOrder: PageFile[] = []
        this.parsed.toc.forEach(t => this.getPagesFromToc(t, pagesInOrder))
        pagesInOrder.forEach(page => spineItems.push(<opf:itemref linear="yes" idref={`idxhtml_${basename(page.newPath)}`} />))

        let i = 0
        for (const resource of allResources) {
            const { mimeType } = resource.parsed

            manifestItems.push(<opf:item media-type={mimeType} id={`idresource_${i}`} href={this.relativeToMe(resource.newPath)} />)
            i++
        }


        const bookMetadata = this.parsed
        // Remove the timezone from the revised_date
        const revised = bookMetadata.revised.replace('+00:00', 'Z')

        return fromJSX(
            <opf:package version='3.0' unique-identifier='uid'>
                <opf:metadata>
                    <dc:title>{bookMetadata.title}</dc:title>
                    <dc:language>{bookMetadata.language}</dc:language>
                    <opf:meta property='dcterms:modified'>{revised}</opf:meta>
                    <opf:meta property='dcterms:license'>{bookMetadata.licenseUrl}</opf:meta>
                    <dc:identifier id='uid'>dummy-openstax.org-id.{bookMetadata.slug}</dc:identifier>
                    <dc:creator>{bookMetadata.authors}</dc:creator>
                </opf:metadata>
                <opf:manifest>
                    <opf:item id='just-the-book-style' media-type='text/css' properties='remote-resources' href='the-style-epub.css' />
                    <opf:item id='nav' properties='nav' media-type='application/xhtml+xml' href={this.relativeToMe(this.tocFile.newPath)} />
                    <opf:item id="the-ncx-file" href={this.relativeToMe(this.ncxFile.newPath)}  media-type="application/x-dtbncx+xml"/>
                    {...manifestItems}
                </opf:manifest>
                <opf:spine toc="the-ncx-file">
                    <opf:itemref linear="yes" idref="nav"/>
                    {...spineItems}
                </opf:spine>
            </opf:package>
        ).node
    }
}

export class NcxFile extends TocFile {
  _idCounter = 1

  private nextId(): number {
   return this._idCounter++;
  }

  private fillNavMap(toc: TocTree): JSXNode {
    if (toc.type == TocTreeType.LEAF) {
        return (
            <ncx:navPoint id={`idm${this.nextId()}`}>
                <ncx:navLabel><ncx:text>{toc.title}</ncx:text></ncx:navLabel>
                <ncx:content src={`./${this.relativeToMe(toc.page.newPath)}`} />
            </ncx:navPoint>
        )
    } else {
        function findFirstLeafPage(toc: TocTree): Opt<PageFile> {
            if (toc.type === TocTreeType.LEAF) return toc.page
            for (const c of toc.children) {
                const ret = findFirstLeafPage(c)
                if (ret !== undefined) return ret
            }
            return undefined
        }
        const firstPage = assertValue(findFirstLeafPage(toc), 'BUG: Could not find an intro page')
        return (
            <ncx:navPoint id={`idm${this.nextId()}`}>
                <ncx:navLabel>
                    <ncx:text>{toc.title}</ncx:text>
                </ncx:navLabel>
                <ncx:content src={this.relativeToMe(firstPage.newPath)} />
                {...toc.children.map(d => this.fillNavMap(d))}
            </ncx:navPoint>
        )
    }
  }

  protected override async convert(): Promise<Node> {
    const { toc, allPages, title, slug } = this.parsed;
    //Find the depth of the table of content
    const depth = Math.max(...toc.map((t) => this.findDepth(t)));

    return fromJSX(
        <ncx:ncx version="2005-1">
            <ncx:head>
                <ncx:meta name='dtb:uid' content={`dummy-openstax.org-id.${slug}`}/>
                <ncx:meta name='dtb:depth' content={depth}/>
                <ncx:meta name='dtb:generator' content='OpenStax EPUB Maker 2022-08'/>
                <ncx:meta name='dtb:pagecount' content={allPages.size}/>
                <ncx:meta name='dtb:maxPageNumber' content={allPages.size}/>
            </ncx:head>
            <ncx:docTitle><ncx:text>{title}</ncx:text></ncx:docTitle>
            <ncx:navMap>{toc.map((t) => this.fillNavMap(t))}</ncx:navMap>
        </ncx:ncx>
    ).node
  }
}
