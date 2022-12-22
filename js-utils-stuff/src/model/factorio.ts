import { resolve } from 'path'
import { Factory } from './factory'
import { ResourceFile } from '../model/file'
import { PageFile } from '../epub/page'
import { OpfFile } from '../epub/toc'

type Builder<T> = (absPath: string) => T

export class Factorio<TBook, TPage, TResource> {
  public readonly books: Factory<TBook>
  public readonly pages: Factory<TPage>
  public readonly resources: Factory<TResource>

  constructor(
    bookBuilder: Builder<TBook>,
    pageBuilder: Builder<TPage>,
    resourceBuilder: Builder<TResource>
  ) {
    this.books = new Factory(bookBuilder, resolve)
    this.pages = new Factory(pageBuilder, resolve)
    this.resources = new Factory(resourceBuilder, resolve)
  }
}
