import { constants, copyFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
import { resolve, relative, join, dirname } from 'path'
import type { Dom } from '../minidom';
import { dom } from '../minidom';
import { assertTrue, assertValue, readXmlWithSourcemap, writeXmlWithSourcemap, XmlFormat } from '../utils'
import type { Factory, Opt } from './factory';
import type { PageFile } from './page';
import type { OpfFile } from './toc';

export type Builder<T> = (absPath: string) => T

export abstract class File<T> {
    private _newPath: Opt<string>
    private _data: Opt<T>
    constructor(public readonly readPath: string) { }
    rename(relPath: string, relTo: Opt<string>) {
        this._newPath = relTo === undefined ? relPath : join(dirname(relTo), relPath)
    }
    public get newPath() {
        return this._newPath || this.readPath
    }
    public readJson<T>(file: string) { return JSON.parse(readFileSync(file, 'utf-8')) as T }

    public get data() {
        return assertValue(this._data, `BUG: File has not been parsed yet: '${this.readPath}'`)
    }

    abstract write(): Promise<void>
    protected abstract innerParse(pageFactory: Factory<PageFile>, resourceFactory?: Factory<ResourceFile>, tocFactory?: Factory<OpfFile>): Promise<T>
    public async parse(pageFactory: Factory<PageFile>, resourceFactory: Factory<ResourceFile>, tocFactory: Factory<OpfFile>) {
        if (this._data !== undefined) {
            console.warn(`BUG? Attempting to parse a file a second time: '${this.readPath}'`)
            return
        }
        const d = await this.innerParse(pageFactory, resourceFactory, tocFactory)
        this._data = d
        // return d
    }
}

export abstract class XMLFile<T> extends File<T> {
    protected relativeToMe(absPath: string) {
        return relative(dirname(this.newPath), absPath)
    }
    protected toAbsolute(relPath: string) {
        return resolve(dirname(this.readPath), relPath)
    }
    protected abstract transform(doc: Dom): Dom
    
    public async readXml(file: string): Promise<Document> { return readXmlWithSourcemap(file) }
    public async writeXml(file: string, root: Node, format: XmlFormat) { writeXmlWithSourcemap(file, root, format) }

    public async write() {
        const doc = dom(await this.readXml(this.readPath))
        const root = this.transform(doc)
        this.writeXml(this.newPath, root.node, XmlFormat.XHTML5)
    }
}


export type ResourceData = {
    mimeType: string
    originalExtension: string
}
export class ResourceFile extends File<ResourceData> {
    static mimetypeExtensions: { [k: string]: string } = {
        'image/jpeg': 'jpeg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/tiff': 'tiff',
        'image/svg+xml': 'svg',
        'audio/mpeg': 'mpg',
        'audio/basic': 'au',
        'application/pdf': 'pdf',
        'application/zip': 'zip',
        'audio/midi': 'midi',
        'audio/x-wav': 'wav',
        // 'text/plain':         'txt',
        'application/x-shockwave-flash': 'swf',
        // 'application/octet-stream':
    }
    private realReadPath() {
        return this.readPath.replace('/resources/', '/IO_RESOURCES/')
    }
    protected async innerParse() {
        const metadataFile = `${this.realReadPath()}.json`
        const json = this.readJson<any>(metadataFile)
        return {
            mimeType: json.mime_type as string,
            originalExtension: json.original_name.split('.').reverse()[0] as string
        }
    }

    public async write() {
        assertTrue(this.readPath !== this.newPath)
        const readPath = this.realReadPath()
        if (!existsSync(this.newPath)) mkdirSync(dirname(this.newPath), { recursive: true })
        copyFileSync(readPath, this.newPath, constants.COPYFILE_EXCL)
    }
}
