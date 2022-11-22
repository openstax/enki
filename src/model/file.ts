import { readFileSync } from 'fs';
import { resolve, relative, join, dirname } from 'path'
import { assertValue, readXmlWithSourcemap, writeXmlWithSourcemap, XmlFormat } from '../utils'
import type { Factory, Opt } from './factory';
import type { PageFile } from './page';

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

    protected abstract innerParse(pageFactory: Factory<PageFile>, resourceFactory?: Factory<ResourceFile>): Promise<T>
    public async parse(pageFactory: Factory<PageFile>, resourceFactory: Factory<ResourceFile>) {
        if (this._data !== undefined) {
            console.warn(`BUG? Attempting to parse a file a second time: '${this.readPath}'`)
            return
        }
        const d = await this.innerParse(pageFactory, resourceFactory)
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
    protected abstract transform(doc: Document): void
    
    public async readXml(file: string): Promise<Document> { return readXmlWithSourcemap(file) }
    public async writeXml(file: string, doc: Document, format: XmlFormat) { writeXmlWithSourcemap(file, doc, format) }

    public async write() {
        const doc = await this.readXml(this.readPath)
        this.transform(doc)
        this.writeXml(this.newPath, doc, XmlFormat.XHTML5)
    }
}

export type ResourceData = {
    mimeType: string
    originalExtension: string
}
export class ResourceFile extends File<ResourceData> {

    protected async innerParse() {
        const metadataFile = `${this.readPath}.json`.replace('/resources/', '/IO_RESOURCES/')
        const json = this.readJson<any>(metadataFile)
        return {
            mimeType: json.mime_type as string,
            originalExtension: json.original_name.split('.').reverse()[0] as string
        }
    }
}
