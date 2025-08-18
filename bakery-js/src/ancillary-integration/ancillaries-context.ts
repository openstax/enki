import FormData from 'form-data'
import { assertValue } from '../utils'
import { acceptStatus } from './utils'

// [200, 400)
export const defaultAcceptRange = [...new Array(200)].map((_, idx) => idx + 200)

export interface FileValue {
  path: string
  label: string
  mimeType: string
  dataType: 'file'
}

export interface FileInput {
  name: string
  type: string
  blob: Buffer
}

export interface UploadConfig {
  url: string
  payload: { [key: string]: string }
}

export interface FieldConfig {
  name: string
  id: string
}

export interface FormatConfig {
  label: string
  id: string
  fields: FieldConfig[]
}

export type AncillaryTypeDocument = Partial<{
  id: string
  fields: FieldConfig[]
  formats: FormatConfig[]
}>

class AncillaryType {
  private _typeDocument: AncillaryTypeDocument | undefined = undefined

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
    options?: {
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
    const okRange = options?.accept ?? defaultAcceptRange
    for (let tries = (options?.retries ?? 2) + 1; tries-- > 0; ) {
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
    const uploaded = []
    if (files.length > 0) {
      const config = await this.authorizeUpload()
      for (let slice = files; (slice = files.splice(0, 10)).length > 0; ) {
        uploaded.push(
          ...(await Promise.all(
            slice.map(async (file) => await this.uploadFile(file, config))
          ))
        )
      }
    }
    return uploaded
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
