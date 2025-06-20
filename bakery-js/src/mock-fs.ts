import { jest } from '@jest/globals'
import fs from 'fs'
import { dirname, resolve, sep } from 'path'
import { Writable } from 'stream'

type FileContent = string | Buffer

interface MockFile {
  [key: string]: FileContent
}

interface MockDirectory {
  [key: string]: FileContent | MockDirectory
}

export type MockFileSystem = MockFile | MockDirectory

const constants = fs.constants

const assertTrue = (v: boolean, message: string) => {
  /* istanbul ignore if */
  if (v !== true) {
    throw new Error(message)
  }
}

const assertValue = <T>(v: T | null | undefined, message: string) => {
  if (v !== null && v !== undefined) return v
  /* istanbul ignore next */
  throw new Error(`BUG: assertValue. Message: ${message}`)
}

const isFileContent = (fs: FileContent | MockDirectory): fs is FileContent =>
  typeof fs === 'string' || Buffer.isBuffer(fs)

type WritableOptions =
  | BufferEncoding
  | {
      flags?: string | undefined
      encoding?: BufferEncoding | undefined
      fd?: number | undefined
      mode?: number | undefined
      autoClose?: boolean | undefined
      emitClose?: boolean | undefined
      start?: number | undefined
      highWaterMark?: number | undefined
    }

class MockWritable extends Writable {
  private _data = ''
  private _encoding: BufferEncoding = 'utf8'

  constructor(
    private path: string,
    private fsMock: FS,
    options: WritableOptions
  ) {
    super({ highWaterMark: 16 * 1024 })
    if (typeof options === 'object' && options.encoding) {
      this._encoding = options.encoding
    } else if (typeof options === 'string') {
      this._encoding = options
    }
  }

  override _write(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chunk: any,
    encoding: BufferEncoding | 'buffer',
    callback: (error?: Error | null) => void
  ): void {
    /* istanbul ignore else (not sure why encoding is always 'buffer') */
    if (encoding === 'buffer') {
      this._data += chunk.toString(this._encoding)
    } else {
      this._data += chunk
    }
    // Simulate disk writes by calling our existing writeFileSync method
    this.fsMock.writeFileSync(this.path, this._data)
    callback()
  }

  // override _final(callback?: () => void): void {
  //   if (callback) callback()
  // }

  close(callback?: () => void): void {
    if (callback) callback()
  }
}

export class FS {
  _tree: MockFileSystem

  constructor(filesystem?: MockFileSystem) {
    this._tree = {}

    this.setupFiles(filesystem)
  }

  private normPath(path: string) {
    return resolve(process.cwd(), path)
  }

  private getDirectory(path: string, parts: string[]): MockDirectory {
    let ptr = this._tree
    for (const part of parts) {
      const entry = assertValue(ptr[part], `Path does not exist: ${path}`)
      if (!isFileContent(entry)) {
        ptr = entry
      } else {
        throw new Error(`File exists: ${path}`)
      }
    }
    return ptr
  }

  private setupFiles(fs?: MockFileSystem): void {
    const recursiveMapFs = (fs: MockFileSystem, pathParts: string[]) => {
      Object.entries(fs).forEach(([path, content]) => {
        const newPathParts = [...pathParts, path]
        const fullPath = this.normPath(newPathParts.join(sep))
        if (isFileContent(content)) {
          const parent = dirname(fullPath)
          // Create parent directory if it does not exist
          this.mkdirSync(parent, { recursive: true })
          this.writeFileSync(fullPath, content)
        } else {
          if (Object.keys(content).length === 0) {
            this.mkdirSync(fullPath)
          } else {
            recursiveMapFs(content, newPathParts)
          }
        }
      })
    }
    this.mkdirSync(process.cwd(), { recursive: true })
    if (fs) {
      recursiveMapFs(fs, [])
    }
  }

  public mkdirSync(path: string, options: { recursive?: boolean } = {}) {
    const { recursive = false } = options
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const lastPart = parts[parts.length - 1]
    let ptr = this._tree
    for (const part of parts) {
      const entry = ptr[part]
      if (isFileContent(entry)) {
        throw new Error(`File exists: ${path}`)
      }
      if (entry === undefined) {
        if (recursive || part === lastPart) {
          ptr[part] = {}
          ptr = ptr[part] as MockDirectory
        } else {
          throw new Error(`Directory does not exist: ${path}`)
        }
      } else {
        ptr = entry
      }
    }
  }

  public existsSync(path: string) {
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const name = parts[parts.length - 1]
    try {
      const directory = this.getDirectory(norm, parts.slice(0, -1))
      return directory[name] !== undefined
    } catch (_) {
      return false
    }
  }

  public readFileSync(
    path: string,
    options?: { encoding?: null | undefined; flag?: string | undefined } | null
  ): string | Buffer {
    const encoding = options?.encoding
    const flag = options?.flag
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const directory = this.getDirectory(norm, parts.slice(0, -1))
    const contents = assertValue(
      directory[parts[parts.length - 1]],
      `Path does not exist: ${path}`
    )
    // TODO: better flag support
    assertTrue(flag === undefined, 'Flag unsupported')
    assertTrue(isFileContent(contents), `Not a file: ${path}`)
    if (Buffer.isBuffer(contents) && encoding != null) {
      return contents.toString(encoding)
    }
    return contents as string | Buffer
  }

  public writeFileSync(
    path: string,
    content: string | Buffer,
    options?: fs.WriteFileOptions
  ) {
    // TODO: options with flag and mode
    assertTrue(options === undefined, 'Options not supported')
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const name = parts[parts.length - 1]
    const directory = this.getDirectory(path, parts.slice(0, -1))
    assertTrue(
      directory[name] === undefined || isFileContent(directory[name]),
      `Directory exists: ${path}`
    )
    directory[name] = content
  }

  public copyFileSync(src: string, dst: string, flags = 0) {
    const { COPYFILE_EXCL: exclusive } = constants
    assertTrue(
      (flags & exclusive) !== exclusive || !this.existsSync(dst),
      `File exists: ${dst}`
    )
    this.writeFileSync(dst, this.readFileSync(src))
  }

  public rmSync(path: string, options: { recursive?: boolean } = {}) {
    const { recursive = false } = options
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const name = parts[parts.length - 1]
    const directory = this.getDirectory(path, parts.slice(0, -1))
    assertTrue(directory[name] !== undefined, `Path does not exist: ${path}`)
    assertTrue(
      recursive || isFileContent(directory[name]),
      `Path is a directory: ${path}`
    )
    delete directory[name]
  }

  public readdirSync(
    path: string,
    options?:
      | { encoding: BufferEncoding | null; withFileTypes?: false | undefined }
      | BufferEncoding
      | null
  ) {
    // TODO: support options like `withFileTypes`
    assertTrue(options === undefined, 'Options not supported')
    const norm = this.normPath(path)
    const parts = norm.split(sep).filter((part) => part)
    const directory = this.getDirectory(path, parts)
    return Object.keys(directory)
  }

  public createWriteStream(path: string, options: WritableOptions = {}) {
    // TODO: better support for options
    return new MockWritable(path, this, options)
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public getFsModule(): Record<string, (...args: any[]) => any> {
    return {
      existsSync: this.existsSync.bind(this),
      readFileSync: this.readFileSync.bind(this),
      readdirSync: this.readdirSync.bind(this),
      writeFileSync: this.writeFileSync.bind(this),
      copyFileSync: this.copyFileSync.bind(this),
      mkdirSync: this.mkdirSync.bind(this),
      rmSync: this.rmSync.bind(this),
      createWriteStream: this.createWriteStream.bind(this),
    }
  }
}

const getMock = (target: object, key: string) => {
  const fsMock = Reflect.get(target, key)
  /* istanbul ignore if (for type inference) */
  if (!jest.isMockFunction(fsMock)) {
    throw new Error(`Not a jest mock: ${key}`)
  }
  return fsMock
}

const _mockfs = (mockFileSystem?: MockFileSystem) => {
  const store = new FS(mockFileSystem)
  const fsModule = store.getFsModule()
  for (const key in fsModule) {
    const fn = fsModule[key]
    getMock(fs, key).mockImplementation(fn)
  }
}

const defaultFS = new FS()
export const mockfs = Object.assign(_mockfs, {
  restore: () => {
    for (const key in defaultFS.getFsModule()) {
      getMock(fs, key).mockRestore()
    }
  },
})
