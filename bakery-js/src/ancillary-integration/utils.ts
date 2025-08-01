import * as fs from 'fs'
import path from 'path'

export interface DirectoryListing {
  root: string
  listing: Array<
    { type: 'file'; relPath: string } | { type: 'directory'; relPath: string }
  >
}

export const listDirectory = (directory: string): DirectoryListing => {
  const listing: DirectoryListing['listing'] = []
  const recurse = (dir: string) => {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    entries.forEach((entry) => {
      const realPath = path.resolve(path.join(dir, entry.name))
      const relPath = path.relative(directory, realPath)
      if (entry.isDirectory()) {
        listing.push({ type: 'directory', relPath })
        recurse(realPath)
      } else if (entry.isFile()) {
        listing.push({ type: 'file', relPath })
      }
    })
  }
  recurse(directory)
  return { root: path.resolve(directory), listing }
}

const mimetypeByExtension = new Map([
  ['.json', 'application/json'],
  ['.pdf', 'application/pdf'],
  ['.swf', 'application/x-shockwave-flash'],
  ['.zip', 'application/zip'],

  ['.au', 'audio/basic'],
  ['.midi', 'audio/midi'],
  ['.mpg', 'audio/mpeg'],
  ['.wav', 'audio/x-wav'],

  ['.gif', 'image/gif'],
  ['.jpeg', 'image/jpeg'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.tiff', 'image/tiff'],

  ['.css', 'text/css'],
  ['.html', 'text/html'],
  ['.js', 'text/javascript'],
])

export const getMimeType = (filePath: string) => {
  const byExt = mimetypeByExtension.get(path.extname(filePath))
  if (byExt !== undefined) {
    return byExt
  } else {
    const metadataFile = `${filePath}.json`
    if (fs.existsSync(metadataFile)) {
      try {
        const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf-8'))
        return metadata['mime_type']
      } catch (e) {
        console.error(e)
      }
    }
    return undefined
  }
}

export const hadUnexpectedError = (
  response: { status: number },
  accept: number[]
) => {
  return !accept.includes(response.status)
}

export const acceptStatus = (response: Response, accept: number[]) => {
  if (hadUnexpectedError(response, accept)) {
    if (!response.bodyUsed) {
      response.text().then(console.log)
    }
    throw new Error(`${response.status}: ${response.statusText}`)
  }
}
