import * as fs from 'fs'
import * as crypto from 'crypto'
import { assertTrue, assertValue } from '../utils'
import path from 'path'
import { listDirectory, getMimeType } from './utils'
import {
  AncillariesContext,
  FileInput,
  mapFields,
  mapFormats,
} from './ancillaries-context'

const testModeId = (id: string) => {
  const hash = crypto.createHash('sha256').update(`test-${id}`).digest('hex')
  // Set UUID version (5) and RFC 4122 variant (10xx) bits so the result is a valid UUID
  const variantNibble = ((parseInt(hash[16], 16) & 0x3) | 0x8).toString(16)
  return [
    hash.slice(0, 8),
    hash.slice(8, 12),
    '5' + hash.slice(13, 16),
    variantNibble + hash.slice(17, 20),
    hash.slice(20, 32),
  ].join('-')
}

export const handleAncillary = async (
  context: AncillariesContext,
  ancillaryPath: string,
  testMode = true
) => {
  const metadataFile = path.join(ancillaryPath, 'metadata.json')
  const metadata = JSON.parse(fs.readFileSync(metadataFile, 'utf-8'))
  const ancillaryTypeName = assertValue(metadata['ancillary_type'])
  const ancillaryType = assertValue(
    context.ancillaryTypesByName[ancillaryTypeName]
  )
  const config = assertValue(ancillaryType.config)
  const formats: { [key: string]: { [key: string]: unknown } } = {}
  const typeDocument = assertValue(await ancillaryType.typeDocument)
  const typeId = assertValue(typeDocument.id)
  const fieldConfigs = assertValue(typeDocument.fields)
  const formatConfigs = assertValue(typeDocument.formats)
  const name = assertValue(metadata['name'])
  const slug = assertValue(metadata['slug'])
  const id = assertValue(metadata['id'])
  const description = metadata['description'] ?? 'No description'
  const relations = metadata['relations'] ?? []
  const htmlFormatLabel = config['htmlFormatLabel']
  if (htmlFormatLabel) {
    const ancillaryListing = listDirectory(ancillaryPath)
    const fileListing = ancillaryListing.listing.filter(
      ({ type }) => type === 'file'
    )
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
    assertTrue(files.length > 0, 'BUG: expected at least 1 file entry')
    formats[htmlFormatLabel] = {
      folder: {
        files,
        dataType: 'folder',
      },
    }
  }
  assertTrue(Object.keys(formats).length > 0, 'BUG: expected at least 1 format')
  const effectiveId = testMode ? testModeId(id) : id
  const fields = {
    name: testMode ? `[test] ${name}` : name,
    description,
    publicationState: testMode ? 'draft' : 'published',
  }
  const mappedFields = mapFields(fields, fieldConfigs)
  const mappedFormats = mapFormats(formats, formatConfigs)
  const payload = {
    type: typeId,
    fields: mappedFields,
    formats: mappedFormats,
    relations,
  }
  return { payload, slug, id: effectiveId, ancillaryTypeName }
}

export const upload = async (ancillariesDir: string, testMode = true) => {
  // Created once and reused for every ancillary below: AncillariesContext
  // memoizes ancillaryTypesByName/typeDocument per instance, so a shared
  // context is what makes type lookups cache across a book instead of
  // re-fetching per ancillary.
  const context = AncillariesContext.fromEnv()
  const ancillaryPaths = fs
    .readdirSync(ancillariesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.resolve(path.join(ancillariesDir, entry.name)))
  for (const ancillaryPath of ancillaryPaths) {
    const filename = path.basename(ancillaryPath)
    console.error(JSON.stringify({ status: 'uploading', filename }))
    const { payload, slug, id, ancillaryTypeName } = await handleAncillary(
      context,
      ancillaryPath,
      testMode
    )
    const docType = ancillaryTypeName
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
