import {
  constants,
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
} from 'fs'
import { resolve, relative, join, dirname } from 'path'
import { DIRNAMES } from '../env'
import {
  assertTrue,
  assertValue,
  readXmlWithSourcemap,
  writeXmlWithSourcemap,
} from '../utils'
import type { Factorio } from '../model/factorio'
import type { Opt } from '../model/factory'

/**
 * Files Read:
 * - META-INF/books.xml
 * - book.toc.xhtml
 *   - book.toc-metadata.json
 * - page.xhtml
 * - image-resource.json
 * - book-style.css
 *
 * Files Written:
 * - container.xml  (from books.xml)
 * - book.opf
 * - book.toc.xhtml (from book.toc.xhtml)
 * - book.ncx
 * - image-resource (from image-resource.json)
 * - book-style.css (from book-style.css)
 */
export abstract class File {
  private _newPath: Opt<string>
  constructor(private readonly _readPath: string) {}
  public rename(relPath: string, relTo?: string) {
    this._newPath =
      relTo === undefined ? relPath : join(dirname(relTo), relPath)
  }
  public get readPath() {
    return assertValue(
      this._readPath,
      'BUG: This appears to be a new File since a readPath was not provided when it was constructed'
    )
  }
  public get newPath() {
    return this._newPath || this.readPath
  }
  readJson<T>(file: string) {
    return JSON.parse(readFileSync(file, 'utf-8')) as T
  }
  public abstract write(): Promise<void>
}

export interface Readable<T, TBook, TPage, TResource> {
  get parsed(): T
  parse(factorio: Factorio<TBook, TPage, TResource>): Promise<void>
}

export abstract class XmlFile<T, TBook, TPage, TResource>
  extends File
  implements Readable<T, TBook, TPage, TResource>
{
  protected _parsed: Opt<T> = undefined
  constructor(readPath: string) {
    super(readPath)
  }
  public get parsed() {
    return assertValue(this._parsed, 'BUG: Forgot to call parse()')
  }
  abstract parse(factorio: Factorio<TBook, TPage, TResource>): Promise<void>
  protected abstract convert(): Promise<Node>
  public async write(): Promise<void> {
    const doc = await this.convert()
    await this.writeXml(doc)
  }
  public async readXml(file = this.readPath): Promise<Document> {
    return readXmlWithSourcemap(file)
  }
  private async writeXml(root: Node, file = this.newPath) {
    await writeXmlWithSourcemap(file, root)
  }

  protected relativeToMe(absPath: string) {
    return relative(dirname(this.newPath), absPath)
  }
  protected toAbsolute(relPath: string) {
    return resolve(dirname(this.readPath), relPath)
  }
}

export type ResourceData = {
  mimeType: string
  originalExtension: string
}

export class ResourceFile
  extends File
  implements Readable<ResourceData, any, any, any>
{
  private _data: Opt<ResourceData> = undefined

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
    return this.readPath.replace('/resources/', `/${DIRNAMES.IO_RESOURCES}/`)
  }

  public get parsed() {
    return assertValue(this._data, 'BUG: Forgot to call parse()')
  }

  async parse(_: Factorio<any, any, any>): Promise<void> {
    const metadataFile = `${this.realReadPath()}.json`
    const json = await this.readJson<any>(metadataFile)
    this._data = {
      mimeType: json.mime_type as string,
      originalExtension: json.original_name.split('.').reverse()[0] as string,
    }
  }

  public async write() {
    assertTrue(this.readPath !== this.newPath)
    const readPath = this.realReadPath()
    try {
      if (!existsSync(this.newPath))
        mkdirSync(dirname(this.newPath), { recursive: true })
      copyFileSync(readPath, this.newPath, constants.COPYFILE_EXCL)
    } catch (error: any) {
      if (error.code == 'EEXIST')
        console.warn(`File already exists! ${this.newPath}`)
      else throw error
    }
  }
}
