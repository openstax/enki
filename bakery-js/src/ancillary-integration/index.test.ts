import {
  jest,
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
} from '@jest/globals'
import { newAncillaryTypeSuperHandler } from './index'
import { AncillariesContext } from './ancillaries-context'
import { mockfs } from '../mock-fs'
import nock from 'nock'

jest.mock('fs')

describe('newAncillaryTypeSuperHandler', () => {
  const host = 'localhost'
  const sharedSecret = 'secret'
  const superTypeId = 'super-type-id'

  let context: AncillariesContext
  const newScope = () => nock(`https://${host}`)

  const typeDocument = {
    id: 'type-doc-id',
    fields: [
      { name: 'name', id: 'name-field-id' },
      { name: 'description', id: 'desc-field-id' },
      { name: 'publicationState', id: 'pub-state-field-id' },
    ],
    formats: [
      {
        label: 'HTML',
        id: 'html-format-id',
        fields: [{ name: 'folder', id: 'folder-field-id' }],
      },
    ],
  }

  const metadata = {
    name: 'My Ancillary',
    slug: 'my-ancillary',
    id: 'original-id',
    description: 'A test ancillary',
  }

  const mockApiPath = (pathParts: string[]) => {
    const url = new URL(context.buildApiPathV0(pathParts))
    url.searchParams.set('sharedSecret', sharedSecret)
    return url.href.replace(url.origin, '')
  }

  const setupTypeDocumentMock = () => {
    newScope()
      .get(mockApiPath(['ancillary-types', superTypeId]))
      .reply(200, typeDocument)
  }

  beforeEach(() => {
    context = new AncillariesContext(
      host,
      { super: { id: superTypeId, htmlFormatLabel: 'HTML' } },
      sharedSecret
    )
    jest.spyOn(context, 'uploadFiles').mockResolvedValue([])
    mockfs({
      '/ancillary': {
        'metadata.json': JSON.stringify(metadata),
        'content.html': '<html></html>',
      },
    })
  })

  afterEach(() => {
    nock.cleanAll()
    jest.restoreAllMocks()
    mockfs.restore()
  })

  describe('normal mode (testMode = false)', () => {
    it('uses the original id from metadata', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, false)
      const { id } = await handler('/ancillary')
      expect(id).toBe('original-id')
    })

    it('does not prefix the name', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, false)
      const { payload } = await handler('/ancillary')
      expect(payload.fields['name-field-id']).toBe('My Ancillary')
    })

    it('sets publicationState to published', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, false)
      const { payload } = await handler('/ancillary')
      expect(payload.fields['pub-state-field-id']).toBe('published')
    })

    it('returns the slug unchanged', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, false)
      const { slug } = await handler('/ancillary')
      expect(slug).toBe('my-ancillary')
    })
  })

  describe('test mode (testMode = true)', () => {
    it('uses a different id than the original', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { id } = await handler('/ancillary')
      expect(id).not.toBe('original-id')
    })

    it('generates a UUID v5-shaped id', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { id } = await handler('/ancillary')
      expect(id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
      )
    })

    it('generates a deterministic id for the same input', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { id: id1 } = await handler('/ancillary')
      const { id: id2 } = await handler('/ancillary')
      expect(id1).toBe(id2)
    })

    it('generates different ids for different original ids', async () => {
      setupTypeDocumentMock()
      const otherMetadata = { ...metadata, id: 'other-id' }
      mockfs({
        '/ancillary': { 'metadata.json': JSON.stringify(metadata) },
        '/other-ancillary': { 'metadata.json': JSON.stringify(otherMetadata) },
      })
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { id: id1 } = await handler('/ancillary')
      const { id: id2 } = await handler('/other-ancillary')
      expect(id1).not.toBe(id2)
    })

    it('prefixes the name with [test]', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { payload } = await handler('/ancillary')
      expect(payload.fields['name-field-id']).toBe('[test] My Ancillary')
    })

    it('sets publicationState to draft', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { payload } = await handler('/ancillary')
      expect(payload.fields['pub-state-field-id']).toBe('draft')
    })

    it('returns the slug unchanged', async () => {
      setupTypeDocumentMock()
      const handler = await newAncillaryTypeSuperHandler(context, true)
      const { slug } = await handler('/ancillary')
      expect(slug).toBe('my-ancillary')
    })
  })

  it('defaults to test mode when no testMode argument is provided', async () => {
    setupTypeDocumentMock()
    const handler = await newAncillaryTypeSuperHandler(context)
    const { id, payload } = await handler('/ancillary')
    expect(id).not.toBe('original-id')
    expect(payload.fields['pub-state-field-id']).toBe('draft')
  })
})
