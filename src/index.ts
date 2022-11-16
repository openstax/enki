import { resolve } from 'path'
import { Factory, Opt } from './factory'
import { assertValue, readXmlWithSourcemap, selectAll } from './utils'

class Factorio {
    public readonly pages = new Factory(absPath => new XHTMLPageFile(this, absPath), resolve)
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


async function fn() {

    const factorio = new Factorio()

    const page = factorio.pages.getOrAdd('../test.xhtml', __filename)
    const info = await page.parse()
    console.log(info)
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
}

fn().catch(err => console.error(err))