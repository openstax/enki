import * as fs from 'fs'
import { assertValue } from '../utils'
import path from 'path'
import { listDirectory, getMimeType } from './utils'
import { AncillariesContext, FileInput } from './ancillaries-context'

interface FieldConfig {
  name: string
  id: string
}

interface FormatConfig {
  label: string
  id: string
  fields: FieldConfig[]
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

export const upload = async (ancillariesDir: string) => {
  const context = AncillariesContext.fromEnv()
  const ancillaryTypeSuperHandler = await newAncillaryTypeSuperHandler(context)
  const ancillaryPaths = fs
    .readdirSync(ancillariesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.resolve(path.join(ancillariesDir, entry.name)))
  for (const ancillaryPath of ancillaryPaths) {
    await ancillaryTypeSuperHandler(ancillaryPath)
  }
}
