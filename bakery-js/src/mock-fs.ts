import { jest } from '@jest/globals'
import fs from 'fs'
import { dirname, resolve, normalize } from 'path'

type FileContent = string | Buffer

interface MockFile {
  [key: string]: FileContent
}

interface MockDirectory {
  [key: string]: FileContent | MockDirectory
}

type MockFileSystem = MockFile | MockDirectory

const constants = {
  COPYFILE_EXCL: 1,
  R_OK: 1 << 1,
  W_OK: 1 << 2,
} as const

type EncodingOptions = { encoding?: BufferEncoding }
type ReadFileOptions = EncodingOptions

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

const isFileContent = (
  fs: FileContent | MockDirectory
): fs is string | Buffer => typeof fs === 'string' || Buffer.isBuffer(fs)

export class FS {
  _tree: MockFileSystem

  constructor(filesystem?: MockFileSystem) {
    this._tree = {}

    if (filesystem) {
      this.setupFiles(filesystem)
    }
  }

  private resolve(...path: string[]) {
    return resolve('/', ...path)
  }

  private normPath(path: string) {
    return normalize(path)
  }

  private getLeaf(path: string, parts: string[]): MockDirectory {
    let ptr = this._tree
    for (const part of parts) {
      const entry = assertValue(ptr[part], `Path does not exist: ${path}`)
      assertTrue(!isFileContent(entry), `File exists: ${path}`)
      ptr = entry as MockDirectory
    }
    return ptr
  }

  private setupFiles(fs: MockFileSystem): void {
    const recursiveMapFs = (fs: MockFileSystem, pathParts: string[]) => {
      Object.entries(fs).forEach(([path, content]) => {
        const newPathParts = [...pathParts, path]
        const fullPath = this.resolve(normalize(newPathParts.join('/')))
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
    recursiveMapFs(fs, [])
  }

  public mkdirSync(path: string, options: { recursive?: boolean } = {}) {
    const { recursive = false } = options
    const norm = this.normPath(path)
    const parts = norm.split('/').filter((part) => part)
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
    const parts = norm.split('/').filter((part) => part)
    const name = parts[parts.length - 1]
    try {
      const parentDir = this.getLeaf(norm, parts.slice(0, -1))
      return !isFileContent(parentDir) && parentDir[name] !== undefined
    } catch (_) {
      return false
    }
  }

  public readFileSync(
    path: string,
    options: ReadFileOptions = {}
  ): string | Buffer {
    const { encoding } = options
    const norm = this.normPath(path)
    const parts = norm.split('/').filter((part) => part)
    const leaf = this.getLeaf(norm, parts.slice(0, -1))
    const contents = assertValue(
      leaf[parts[parts.length - 1]],
      `Path does not exist: ${path}`
    )
    assertTrue(isFileContent(contents), `Not a file: ${path}`)
    if (Buffer.isBuffer(contents) && encoding !== undefined) {
      return contents.toString(encoding)
    }
    return contents as string | Buffer
  }

  public writeFileSync(path: string, content: string | Buffer) {
    // TODO: options with flags
    const norm = this.normPath(path)
    const parts = norm.split('/').filter((part) => part)
    const name = parts[parts.length - 1]
    const directory = this.getLeaf(path, parts.slice(0, -1))
    assertTrue(
      directory[name] === undefined || isFileContent(directory[name]),
      `Directory exists: ${path}`
    )
    directory[parts[parts.length - 1]] = content
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
    const norm = normalize(path)
    const parts = norm.split('/').filter((part) => part)
    const name = parts[parts.length - 1]
    const leaf = this.getLeaf(path, parts.slice(0, -1))
    assertTrue(leaf[name] !== undefined, `Path does not exist: ${path}`)
    assertTrue(
      recursive || isFileContent(leaf[name]),
      `Path is a directory: ${path}`
    )
    delete leaf[name]
  }

  public readdirSync(path: string, options = undefined) {
    assertTrue(options === undefined, 'Options not supported')
    const norm = this.normPath(path)
    const parts = norm.split('/').filter((part) => part)
    const directory = this.getLeaf(path, parts)
    return Object.keys(directory)
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public getFsModule(): Record<string, any> {
    return {
      existsSync: this.existsSync.bind(this),
      readFileSync: this.readFileSync.bind(this),
      readdirSync: this.readdirSync.bind(this),
      writeFileSync: this.writeFileSync.bind(this),
      copyFileSync: this.copyFileSync.bind(this),
      mkdirSync: this.mkdirSync.bind(this),
      rmSync: this.rmSync.bind(this),
    }
  }
}

// const memoryFS = (fs: MockFileSystem) => {
//   const tree: MockFileSystem = {}
//   const getLeaf = (path: string, parts: string[]) => {
//     let ptr = tree
//     for (const part of parts) {
//       const entry = assertValue(ptr[part], `Path does not exist: ${path}`)
//       assertTrue(!isFileContent(entry), `File exists: ${path}`)
//       ptr = entry as MockDirectory
//     }
//     return ptr
//   }
//   const normPath = (path: string) => normalize(path)
//   const existsSync = (path: string) => {
//     const norm = normPath(path)
//     const parts = norm.split('/').filter((part) => part)
//     return getLeaf(norm, parts) !== undefined
//   }
//   const readFileSync = (path: string, options: ReadFileOptions = {}) => {
//     const { encoding } = options
//     const norm = normPath(path)
//     const parts = norm.split('/').filter((part) => part)
//     const leaf = getLeaf(norm, parts.slice(0, -1))
//     const contents = assertValue(leaf[parts[parts.length - 1]])
//     assertTrue(isFileContent(contents), `Not a file: ${path}`)
//     if (Buffer.isBuffer(contents) && encoding !== undefined) {
//       return contents.toString(encoding)
//     }
//     return contents as string | Buffer
//   }
//   const writeFileSync = (path: string, content: string | Buffer) => {
//     // TODO: options with flags
//     const norm = normPath(path)
//     const parts = norm.split('/').filter((part) => part)
//     const name = parts[parts.length - 1]
//     const leaf = getLeaf(path, parts.slice(0, -1))
//     const directory = assertValue(!isFileContent(leaf) ? leaf : undefined)
//     assertTrue(
//       directory[name] === undefined || isFileContent(directory[name]),
//       `Directory exists: ${path}`
//     )
//     directory[parts[parts.length - 1]] = content
//   }
//   const mkdirSync = (path: string, options: { recursive?: boolean } = {}) => {
//     const { recursive = false } = options
//     const parts = path.split('/').filter((part) => part)
//     const lastPart = parts[parts.length - 1]
//     let ptr = tree
//     for (const part of parts) {
//       const entry = ptr[part]
//       if (isFileContent(entry)) {
//         throw new Error(`File exists: ${path}`)
//       }
//       if (entry === undefined) {
//         if (recursive || part === lastPart) {
//           ptr[part] = {}
//           ptr = ptr[part] as MockDirectory
//         } else {
//           throw new Error(`Directory does not exist: ${path}`)
//         }
//       } else {
//         ptr = entry
//       }
//     }
//   }
//   const rmSync = (path: string, options: { recursive?: boolean } = {}) => {
//     const { recursive = false } = options
//     const norm = normalize(path)
//     const parts = norm.split('/').filter((part) => part)
//     const name = parts[parts.length - 1]
//     const leaf = getLeaf(path, parts.slice(0, -1))
//     assertTrue(leaf[name] !== undefined, `Path does not exist: ${path}`)
//     assertTrue(
//       recursive || isFileContent(leaf[name]),
//       `Path is a directory: ${path}`
//     )
//     delete leaf[name]
//   }
//   const copyFileSync = (src: string, dst: string, flags = 0) => {
//     // TODO: other flags
//     const { COPYFILE_EXCL: exclusive } = constants
//     assertTrue(
//       (flags & exclusive) !== exclusive || !existsSync(dst),
//       `File exists: ${dst}`
//     )
//     writeFileSync(dst, readFileSync(src))
//   }
//   const readdirSync = (path: string, options = undefined) => {
//     assertTrue(options === undefined, 'Options not supported')
//     const norm = normalize(path)
//     const parts = norm.split('/').filter((part) => part)
//     const leaf = getLeaf(path, parts)
//     const directory = assertValue(!isFileContent(leaf) ? leaf : undefined)
//     return Object.keys(directory)
//   }
//   const recursiveMapFs = (fs: MockFileSystem, pathParts: string[]) => {
//     Object.entries(fs).forEach(([path, content]) => {
//       const newPathParts = [...pathParts, path]
//       const fullPath = resolve('/', normalize(newPathParts.join('/')))
//       if (isFileContent(content)) {
//         const parent = dirname(fullPath)
//         // Create parent directory if it does not exist
//         mkdirSync(parent, { recursive: true })
//         writeFileSync(fullPath, content)
//       } else {
//         recursiveMapFs(content, newPathParts)
//       }
//     })
//   }
//   recursiveMapFs(fs, [])
//   return {
//     existsSync,
//     readFileSync,
//     writeFileSync,
//     mkdirSync,
//     rmSync,
//     copyFileSync,
//     readdirSync,
//   }
// }

const getMock = (target: object, key: string) => {
  const fsMock = Reflect.get(target, key)
  /* istanbul ignore if */
  if (!jest.isMockFunction(fsMock)) {
    throw new Error(`Not a jest mock: ${key}`)
  }
  return fsMock
}

const _mockfs = (mockFileSystem: MockFileSystem) => {
  const store = new FS(mockFileSystem)
  const fsModule = store.getFsModule()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // const fsModule = memoryFS(mockFileSystem) as Record<string, any>
  for (const key in fsModule) {
    const fn = fsModule[key]
    getMock(fs, key).mockImplementation(fn)
  }
  getMock(fs, 'constantsGetter').mockImplementation((key) => {
    if (typeof key === 'string' && Object.keys(constants).includes(key)) {
      return constants[key as keyof typeof constants]
    }
    /* istanbul ignore next */
    return undefined
  })
}

const defaultFS = new FS()
export const mockfs = Object.assign(_mockfs, {
  restore: () => {
    for (const key in defaultFS.getFsModule()) {
      const fsMock = Reflect.get(fs, key) as jest.Mock
      fsMock.mockRestore()
    }
    getMock(fs, 'constantsGetter').mockRestore()
  },
})

// const fs = new FS({
//   '/a/b/c': 'test',
//   'a/d': 'test2',
//   a: {
//     b: {
//       z: 'test3',
//     },
//   },
//   'x/y/z/w': 'something',
// })

/*
{
  a: {
    b: {
      c: 'test'
    }
  }
}
*/

// fs.mkdirSync('/t/r/e/e/e/e', { recursive: true })
// console.log(fs._tree)

// fs.writeFileSync('/t/r/e/e/e/e/a.txt', 'some text')
// console.log(fs.readFileSync('/a/b/z'))
// console.log(fs.readFileSync('/a/b/c'))
// console.log(fs.readFileSync('/x/y/z/w'))
// console.log(fs.readFileSync('/t/r/e/e/e/e/a.txt'))
// console.log(fs.existsSync('/t/r/e/e/e/e/a.txt'))
// fs.mkdirSync('/b')
// fs.copyFileSync('/a/d', '/b/c')
// console.log(fs._tree)
// console.log(fs.readFileSync('/b/c'))
// fs.rmSync('/b', { recursive: true })
// console.log(fs._tree)

// console.log(fs.readdirSync('/a/b'))

/*
WriteStream
createWriteStream
*/
