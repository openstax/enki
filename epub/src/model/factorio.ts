import { resolve } from "path"
import { Factory } from "./factory"
import { Builder, ResourceFile } from "./file"
import { PageFile } from "./page"
import { TocFile } from "./toc"

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

export const factorio: Factorio = new Factorio(
    absPath => new PageFile(absPath),
    absPath => new TocFile(absPath),
    absPath => new ResourceFile(absPath),
)
