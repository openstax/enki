import { resolve } from 'path'
import { Factory, Opt } from './factory'
import { assertValue, readXmlWithSourcemap, selectAll, selectOne } from './utils'

class Factorio {
    public readonly pages = new Factory(absPath => new XHTMLPageFile(this, absPath), resolve)
    public readonly tocs = new Factory(absPath => new XHTMLTocFile(this, absPath), resolve)
    public readonly resources = new Factory(absPath => new ResourceFile(this, absPath), resolve)
}

abstract class File {
    private _newPath: Opt<string>
    constructor(protected readonly factorio: Factorio, protected readonly absPath: string) { }
    rename(newPath: string) {
        this._newPath = newPath
    }
    public newPath() {
        return this._newPath || this.absPath
    }
    // abstract transform(): void
}

class ResourceFile extends File { }

type PropsAndResources = {
    hasMathML: boolean
    hasRemoteResources: boolean
    hasScripts: boolean
    resources: ResourceFile[]
}
class XHTMLPageFile extends File {
    async parse(): Promise<PropsAndResources> {
        const doc = await readXmlWithSourcemap(this.absPath)
        const resources = selectAll<Element>('//h:img', doc).map(img => this.factorio.resources.getOrAdd(assertValue(img.getAttribute('src')), this.absPath))
        return {
            hasMathML: selectAll('//m:math', doc).length > 0,
            hasRemoteResources: selectAll('//h:iframe|//h:object/h:embed', doc).length > 0,
            hasScripts: selectAll('//h:script', doc).length > 0,
            resources
        }
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
    } else { throw new Error('BUG: expected first child in Toc to be a Page') }
}

fn().catch(err => console.error(err))