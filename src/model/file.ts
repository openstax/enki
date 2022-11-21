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
    constructor(protected readonly factorio: Factorio, public readonly origPath: string) { }
    rename(relPath: string, relTo: Opt<string>) {
        this._newPath = relTo === undefined ? relPath : join(dirname(relTo), relPath)
    }
    public newPath() {
        return this._newPath || this.origPath
    }
}

export abstract class XMLFile extends File {
    protected relativeToMe(absPath: string) {
        return relative(dirname(this.newPath()), absPath)
    }
    protected abstract transform(doc: Document): void
    public async write() {
        const doc = await readXmlWithSourcemap(this.origPath)
        this.transform(doc)
        writeXmlWithSourcemap(this.newPath(), doc, XmlFormat.XHTML5)
    }
}

export class ResourceFile extends File {

    async parse() {
        const metadataFile = `${this.origPath}.json`
        const json = JSON.parse(readFileSync(metadataFile, 'utf-8'))
        return {
            mimeType: json.mime_type as string,
            originalExtension: json.original_name.split('.').reverse()[0] as string
        }
    }
}
