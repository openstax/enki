import * as fs from 'fs'
import { assertValue } from '../utils'
import path from 'path'
import { listDirectory, getMimeType, acceptStatus } from './utils'
import FormData from 'form-data'

// [200, 400)
const defaultAcceptRange = [...new Array(200)].map((_, idx) => idx + 200)

interface FileValue {
  path: string
  label: string
  mimeType: string
  dataType: 'file'
}

interface FileInput {
  name: string
  type: string
  blob: Buffer
}

interface UploadConfig {
  url: string
  payload: { [key: string]: string }
}

interface FieldConfig {
  name: string
  id: string
}

interface FormatConfig {
  label: string
  id: string
  fields: FieldConfig[]
}

class AncillaryType {
  private _typeDocument: { [key: string]: unknown } | undefined = undefined

  constructor(
    protected readonly typeId: string,
    protected readonly context: AncillariesContext,
    public readonly config: { [key: string]: string }
  ) {}

  get typeDocument() {
    return (async () => {
      if (this._typeDocument === undefined) {
        this._typeDocument = await this.context.getType(this.typeId)
      }
      return this._typeDocument
    })()
  }
}

export class AncillariesContext {
  private readonly baseUrl: string
  private _ancillaryTypesByName: { [key: string]: AncillaryType } | undefined

  constructor(
    readonly host: string,
    readonly ancillaryTypeConfig: { [key: string]: { [key: string]: string } },
    readonly sharedSecret: string
  ) {
    this.baseUrl = `https://${host.replace(/\/$/, '')}`
  }

  get ancillaryTypesByName() {
    if (this._ancillaryTypesByName === undefined) {
      this._ancillaryTypesByName = Object.fromEntries(
        Object.entries(this.ancillaryTypeConfig).map(([name, config]) => [
          name,
          new AncillaryType(config.id, this, config),
        ])
      )
    }
    return this._ancillaryTypesByName
  }

  buildPath(
    pathParts: string[],
    queryString: { [key: string]: string | undefined } = {}
  ) {
    const filtered: { [k: string]: string } = Object.fromEntries(
      Object.entries(queryString).filter(
        (t): t is [string, string] => typeof t[1] === 'string'
      )
    )
    const searchParams = new URLSearchParams(filtered)
    const url = new URL(
      [`${this.baseUrl}/${pathParts.join('/')}`, searchParams.toString()]
        .filter((s) => s.length > 0)
        .join('?')
    )
    return url.toString()
  }

  buildApiPathV0(
    pathParts: string[],
    queryString: { [key: string]: string | undefined } = {}
  ) {
    return this.buildPath(['api', 'v0', ...pathParts], queryString)
  }

  async fetch(
    input: string | URL,
    options: {
      init?: Parameters<typeof fetch>[1]
      withAuth?: boolean
      retries?: number
      accept?: number[]
    }
  ) {
    if (options?.withAuth === true) {
      const parsed = new URL(input)
      parsed.searchParams.set('sharedSecret', this.sharedSecret)
      input = parsed
    }
    const okRange = options.accept ?? defaultAcceptRange
    for (let tries = (options.retries ?? 2) + 1; tries-- > 0; ) {
      try {
        const response = await acceptStatus(
          await fetch(input, options?.init),
          okRange
        )
        return response
      } catch (e) {
        const hi = 2000
        const lo = 500
        const waitTime = Math.round(Math.random() * (hi - lo) + lo)
        await new Promise((resolve) => setTimeout(resolve, waitTime))
        console.error(e)
      }
    }
    throw new Error('Maximum retries exceeded')
  }

  async getType(typeId: string) {
    const url = this.buildApiPathV0(['ancillary-types', typeId])
    const response = await acceptStatus(
      await this.fetch(url, { withAuth: true }),
      [200]
    )
    return await response.json()
  }

  async authorizeUpload() {
    const url = this.buildApiPathV0(['files', 'authorize-upload'])
    const response = await acceptStatus(
      await this.fetch(url, { withAuth: true }),
      [200]
    )
    return await response.json()
  }

  async uploadFile(file: FileInput, config: UploadConfig) {
    const bucketKey = config.payload.key.replace('${filename}', file.name)
    const response: FileValue = {
      path: bucketKey,
      label: file.name,
      mimeType: file.type,
      dataType: 'file',
    }
    const formData = new FormData()

    Object.entries(config.payload).forEach(([k, v]) => {
      if (k === 'key') {
        v = bucketKey
      }
      formData.append(k, v)
    })

    formData.append('file', file.blob, {
      contentType: file.type,
      filepath: file.name,
    })

    await this.fetch(config.url, {
      init: {
        method: 'POST',
        body: formData.getBuffer(),
        headers: formData.getHeaders(),
      },
    })

    return response
  }

  async uploadFiles(files: FileInput[]) {
    const config = await this.authorizeUpload()
    return await Promise.all(
      files.map(async (file) => {
        return await this.uploadFile(file, config)
      })
    )
  }

  async writeAncillary(id: string, ancillaryJSON: string) {
    const url = this.buildApiPathV0(['ancillaries', id])
    const response = await acceptStatus(
      await this.fetch(url, {
        init: {
          method: 'POST',
          body: ancillaryJSON,
          headers: {
            'Content-Type': 'application/json',
          },
        },
        withAuth: true,
      }),
      [200, 201]
    )
    return response.json()
  }

  static fromEnv() {
    return new AncillariesContext(
      assertValue(process.env.ANCILLARIES_HOST),
      JSON.parse(assertValue(process.env.ANCILLARY_TYPE_CONFIG)),
      assertValue(process.env.ANCILLARIES_SHARED_SECRET)
    )
  }
}

const mapFields = (
  fields: { [key: string]: unknown },
  fieldConfigs: FieldConfig[]
) => {
  return Object.fromEntries(
    Object.entries(fields)
      .map(([k, v]) => {
        const config = fieldConfigs.find((f) => f.name === k)
        return config === undefined ? undefined : [config.id, v]
      })
      .filter(<T>(t: T | undefined): t is T => t !== undefined)
  )
}

const mapFormats = (
  formats: { [key: string]: { [key: string]: unknown } },
  formatConfigs: FormatConfig[]
) => {
  return Object.fromEntries(
    Object.entries(formats)
      .map(([k, v]) => {
        const config = formatConfigs.find((f) => f.label === k)
        return config === undefined
          ? undefined
          : [config.id, { fields: mapFields(v, config.fields) }]
      })
      .filter(<T>(t: T | undefined): t is T => t !== undefined)
  )
}

export const newAncillaryTypeSuperHandler = async (
  context: AncillariesContext
) => {
  const typeSuper = assertValue(context.ancillaryTypesByName['super'])
  const superConfig = assertValue(typeSuper.config)
  const typeDocument = assertValue(await typeSuper.typeDocument)
  const htmlFormatLabel = assertValue(superConfig['htmlFormatLabel'])
  const typeId = assertValue(typeDocument.id) as string
  const fieldConfigs = assertValue(typeDocument.fields) as FieldConfig[]
  const formatConfigs = assertValue(typeDocument.formats) as FormatConfig[]

  return async (ancillaryPath: string) => {
    const ancillaryListing = listDirectory(ancillaryPath)
    const fileListing = ancillaryListing.listing.filter(
      ({ type }) => type === 'file'
    )
    const metadataFile = path.join(ancillaryPath, 'metadata.json')
    const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf-8'))
    const name = assertValue(metadata['name'])
    const id = assertValue(metadata['id'])
    const description = metadata['description'] ?? 'No description'
    const filesInputs: FileInput[] = fileListing.map(({ relPath }) => {
      const realPath = path.resolve(path.join(ancillaryListing.root, relPath))
      const mimeType = getMimeType(realPath) ?? ''
      return {
        name: relPath,
        type: mimeType,
        get blob() {
          return fs.readFileSync(realPath)
        },
      }
    })
    const files = await context.uploadFiles(filesInputs)
    const fields = {
      name,
      description,
      publicationState: 'published',
    }
    const formats = {
      [htmlFormatLabel]: {
        folder: {
          files,
          dataType: 'folder',
        },
      },
    }
    const mappedFields = mapFields(fields, fieldConfigs)
    const mappedFormats = mapFormats(formats, formatConfigs)
    const payload = {
      type: typeId,
      fields: mappedFields,
      formats: mappedFormats,
    }
    const ancillaryJSON = JSON.stringify(payload)
    return await context.writeAncillary(id, ancillaryJSON)
  }
}

export const upload = async (
  context: AncillariesContext,
  ancillariesDir: string
) => {
  const ancillaryTypeSuperHandler = await newAncillaryTypeSuperHandler(context)
  const ancillaryPaths = fs
    .readdirSync(ancillariesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.resolve(path.join(ancillariesDir, entry.name)))
  for (const ancillaryPath of ancillaryPaths) {
    await ancillaryTypeSuperHandler(ancillaryPath)
  }
}
