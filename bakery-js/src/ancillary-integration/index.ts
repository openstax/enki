import * as fs from 'fs'
import { assertValue } from '../utils'
import path from 'path'
import { listDirectory, getMimeType } from './utils'
import {
  AncillariesContext,
  FileInput,
  mapFields,
  mapFormats,
} from './ancillaries-context'

export const newAncillaryTypeSuperHandler = async (
  context: AncillariesContext
) => {
  const typeSuper = assertValue(context.ancillaryTypesByName['super'])
  const superConfig = assertValue(typeSuper.config)
  const typeDocument = assertValue(await typeSuper.typeDocument)
  const htmlFormatLabel = assertValue(superConfig['htmlFormatLabel'])
  const typeId = assertValue(typeDocument.id)
  const fieldConfigs = assertValue(typeDocument.fields)
  const formatConfigs = assertValue(typeDocument.formats)

  return async (ancillaryPath: string) => {
    const ancillaryListing = listDirectory(ancillaryPath)
    const fileListing = ancillaryListing.listing.filter(
      ({ type }) => type === 'file'
    )
    const metadataFile = path.join(ancillaryPath, 'metadata.json')
    const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf-8'))
    const name = assertValue(metadata['name'])
    const slug = assertValue(metadata['slug'])
    const id = assertValue(metadata['id'])
    const description = metadata['description'] ?? 'No description'
    const relations = metadata['relations'] ?? []
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
      relations,
    }
    return { payload, slug, id }
  }
}

export const upload = async (ancillariesDir: string) => {
  const context = AncillariesContext.fromEnv()
  const ancillaryTypeSuperHandler = await newAncillaryTypeSuperHandler(context)
  const ancillaryPaths = fs
    .readdirSync(ancillariesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.resolve(path.join(ancillariesDir, entry.name)))
  for (const ancillaryPath of ancillaryPaths) {
    const filename = path.basename(ancillaryPath)
    console.error(JSON.stringify({ status: 'uploading', filename }))
    const docType = 'super'
    const { payload, slug, id } = await ancillaryTypeSuperHandler(ancillaryPath)
    const ancillaryJSON = JSON.stringify(payload)
    const writeResponse = await context.writeAncillary(id, ancillaryJSON)
    const changed = writeResponse.status === 201
    const compiled = await context.getCompiled(id)
    const defaultFormat = assertValue(
      compiled.defaultFormat,
      'failed to get default format'
    )
    const formatUrl = assertValue(
      defaultFormat.url,
      'failed to get format url'
    ).replace(/^\//, '')
    const url = `${context.baseUrl}/${formatUrl}`
    console.error(
      JSON.stringify({ status: 'complete', id, slug, changed, type: docType })
    )
    console.log(JSON.stringify({ slug, type: docType, id, url }))
  }
}
