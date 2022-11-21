import { readFileSync } from 'fs';
import { resolve, relative, join, dirname } from 'path'
import { Factory, Opt } from './factory'
import { readXmlWithSourcemap, writeXmlWithSourcemap, XmlFormat } from '../utils'
import type { PageFile } from './page';
import type { TocFile } from './toc';

export type Builder<T> = (absPath: string) => T

export class Factorio {
    public readonly pages: Factory<PageFile>
    public readonly tocs: Factory<TocFile>
    public readonly resources: Factory<ResourceFile>
    
    constructor(pageBuilder: Builder<PageFile>, tocBuilder: Builder<TocFile>, resourceBuilder: Builder<ResourceFile>) {
        this.pages = new Factory(pageBuilder, resolve)
        this.tocs = new Factory(tocBuilder, resolve)
        this.resources = new Factory(resourceBuilder, resolve)
    }
}

export abstract class File {
    private _newPath: Opt<string>
    constructor(protected readonly factorio: Factorio, public readonly readPath: string) { }
    rename(relPath: string, relTo: Opt<string>) {
        this._newPath = relTo === undefined ? relPath : join(dirname(relTo), relPath)
    }
    public newPath() {
        return this._newPath || this.readPath
    }
    public readJson<T>(file: string) { return JSON.parse(readFileSync(file, 'utf-8')) as T }
}

export abstract class XMLFile extends File {
    protected relativeToMe(absPath: string) {
        return relative(dirname(this.newPath()), absPath)
    }
    protected abstract transform(doc: Document): void
    
    public async readXml(file: string): Promise<Document> { return readXmlWithSourcemap(file) }
    public async writeXml(file: string, doc: Document, format: XmlFormat) { writeXmlWithSourcemap(file, doc, format) }

    public async write() {
        const doc = await this.readXml(this.readPath)
        this.transform(doc)
        this.writeXml(this.newPath(), doc, XmlFormat.XHTML5)
    }
}

export class ResourceFile extends File {

    async parse() {
        const metadataFile = `${this.readPath}.json`
        const json = this.readJson<any>(metadataFile)
        return {
            mimeType: json.mime_type as string,
            originalExtension: json.original_name.split('.').reverse()[0] as string
        }
    }
}
