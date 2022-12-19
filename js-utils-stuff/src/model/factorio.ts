import { resolve } from 'path'
import { Factory } from './factory'
import { ResourceFile } from './file'
import { PageFile } from './page'
import { OpfFile } from './toc'

type Builder<T> = (absPath: string) => T

export class Factorio {
  public readonly pages: Factory<PageFile>
  public readonly opfs: Factory<OpfFile>
  public readonly resources: Factory<ResourceFile>

  constructor(
    pageBuilder: Builder<PageFile>,
    tocBuilder: Builder<OpfFile>,
    resourceBuilder: Builder<ResourceFile>
  ) {
    this.pages = new Factory(pageBuilder, resolve)
    this.opfs = new Factory(tocBuilder, resolve)
    this.resources = new Factory(resourceBuilder, resolve)
  }
}

export const factorio: Factorio = new Factorio(
  (absPath) => new PageFile(absPath),
  (absPath) => new OpfFile(absPath),
  (absPath) => new ResourceFile(absPath)
)
