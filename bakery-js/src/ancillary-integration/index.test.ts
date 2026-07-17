import {
  jest,
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
} from '@jest/globals'
import { handleAncillary, testModeId } from './index'
import { AncillariesContext } from './ancillaries-context'
import { mockfs } from '../mock-fs'
import nock from 'nock'

jest.mock('fs')

describe('handleAncillary', () => {
  const host = 'localhost'
  const sharedSecret = 'secret'
  const superTypeId = 'super-type-id'
  const otherTypeId = 'other-type-id'

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

  const otherTypeDocument = {
    id: 'other-type-doc-id',
    fields: [
      { name: 'name', id: 'other-name-field-id' },
      { name: 'description', id: 'other-desc-field-id' },
      { name: 'publicationState', id: 'other-pub-state-field-id' },
    ],
    formats: [
      {
        label: 'HTML',
        id: 'other-html-format-id',
        fields: [{ name: 'folder', id: 'other-folder-field-id' }],
      },
    ],
  }

  const metadata = {
    name: 'My Ancillary',
    slug: 'my-ancillary',
    id: 'original-id',
    description: 'A test ancillary',
    ancillary_type: 'super',
  }

  const mockApiPath = (pathParts: string[]) => {
    const url = new URL(context.buildApiPathV0(pathParts))
    url.searchParams.set('sharedSecret', sharedSecret)
    return url.href.replace(url.origin, '')
  }

  const effectiveId = (rawId: string, testMode: boolean) =>
    testMode ? testModeId(rawId) : rawId

  const setupTypeDocumentMock = () => {
    newScope()
      .get(mockApiPath(['ancillary-types', superTypeId]))
      .reply(200, typeDocument)
  }

  const setupOtherTypeDocumentMock = () => {
    newScope()
      .get(mockApiPath(['ancillary-types', otherTypeId]))
      .reply(200, otherTypeDocument)
  }

  const mockRawAncillaryNotFound = (id: string) => {
    newScope()
      .get(mockApiPath(['ancillaries', id, 'raw']))
      .reply(404, { message: 'requested item not found' })
  }

  const mockRawAncillaryExists = (id: string, existingTypeId: string) => {
    newScope()
      .get(mockApiPath(['ancillaries', id, 'raw']))
      .reply(200, { type: existingTypeId })
  }

  beforeEach(() => {
    context = new AncillariesContext(
      host,
      {
        super: { id: superTypeId, htmlFormatLabel: 'HTML' },
        other: { id: otherTypeId, htmlFormatLabel: 'HTML' },
      },
      sharedSecret
    )
    jest.spyOn(context, 'uploadFiles').mockResolvedValue([
      {
        path: 'some/path',
        label: 'content.html',
        mimeType: 'text/html',
        dataType: 'file',
      },
    ])
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
      mockRawAncillaryNotFound('original-id')
      const { id } = await handleAncillary(context, '/ancillary', false)
      expect(id).toBe('original-id')
    })

    it('does not prefix the name', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      const { payload } = await handleAncillary(context, '/ancillary', false)
      expect(payload.fields['name-field-id']).toBe('My Ancillary')
    })

    it('sets publicationState to published', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      const { payload } = await handleAncillary(context, '/ancillary', false)
      expect(payload.fields['pub-state-field-id']).toBe('published')
    })

    it('returns the slug unchanged', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      const { slug } = await handleAncillary(context, '/ancillary', false)
      expect(slug).toBe('my-ancillary')
    })
  })

  describe('test mode (testMode = true)', () => {
    it('uses a different id than the original', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { id } = await handleAncillary(context, '/ancillary', true)
      expect(id).not.toBe('original-id')
    })

    it('generates a UUID v5-shaped id', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { id } = await handleAncillary(context, '/ancillary', true)
      expect(id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
      )
    })

    it('generates a deterministic id for the same input', async () => {
      setupTypeDocumentMock()
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { id: id1 } = await handleAncillary(context, '/ancillary', true)
      const { id: id2 } = await handleAncillary(context, '/ancillary', true)
      expect(id1).toBe(id2)
    })

    it('generates different ids for different original ids', async () => {
      setupTypeDocumentMock()
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      mockRawAncillaryNotFound(effectiveId('other-id', true))
      const otherMetadata = { ...metadata, id: 'other-id' }
      mockfs({
        '/ancillary': { 'metadata.json': JSON.stringify(metadata) },
        '/other-ancillary': { 'metadata.json': JSON.stringify(otherMetadata) },
      })
      const { id: id1 } = await handleAncillary(context, '/ancillary', true)
      const { id: id2 } = await handleAncillary(
        context,
        '/other-ancillary',
        true
      )
      expect(id1).not.toBe(id2)
    })

    it('prefixes the name with [test]', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { payload } = await handleAncillary(context, '/ancillary', true)
      expect(payload.fields['name-field-id']).toBe('[test] My Ancillary')
    })

    it('sets publicationState to draft', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { payload } = await handleAncillary(context, '/ancillary', true)
      expect(payload.fields['pub-state-field-id']).toBe('draft')
    })

    it('returns the slug unchanged', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound(effectiveId('original-id', true))
      const { slug } = await handleAncillary(context, '/ancillary', true)
      expect(slug).toBe('my-ancillary')
    })
  })

  it('defaults to test mode when no testMode argument is provided', async () => {
    setupTypeDocumentMock()
    mockRawAncillaryNotFound(effectiveId('original-id', true))
    const { id, payload } = await handleAncillary(context, '/ancillary')
    expect(id).not.toBe('original-id')
    expect(payload.fields['pub-state-field-id']).toBe('draft')
  })

  describe('multi-type dispatch', () => {
    it('resolves the type named in metadata, not a hardcoded one', async () => {
      setupOtherTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      mockfs({
        '/ancillary': {
          'metadata.json': JSON.stringify({
            ...metadata,
            ancillary_type: 'other',
          }),
          'content.html': '<html></html>',
        },
      })
      const { payload, ancillaryTypeName } = await handleAncillary(
        context,
        '/ancillary',
        false
      )
      expect(ancillaryTypeName).toBe('other')
      expect(payload.type).toBe('other-type-doc-id')
      expect(payload.fields['other-name-field-id']).toBe('My Ancillary')
    })

    it('returns the resolved ancillaryTypeName alongside the payload', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      const result = await handleAncillary(context, '/ancillary', false)
      expect(result.ancillaryTypeName).toBe('super')
    })

    it('throws for a type name with no matching config entry', async () => {
      mockfs({
        '/ancillary': {
          'metadata.json': JSON.stringify({
            ...metadata,
            ancillary_type: 'nonexistent',
          }),
          'content.html': '<html></html>',
        },
      })
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).rejects.toThrow()
    })

    it('throws when metadata has no ancillary_type at all', async () => {
      const { ancillary_type: _unused, ...metadataWithoutType } = metadata
      mockfs({
        '/ancillary': {
          'metadata.json': JSON.stringify(metadataWithoutType),
          'content.html': '<html></html>',
        },
      })
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).rejects.toThrow()
    })
  })

  describe('format guards', () => {
    it('throws when there are no files to upload for the html format', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      jest.spyOn(context, 'uploadFiles').mockResolvedValue([])
      mockfs({
        '/ancillary': {
          'metadata.json': JSON.stringify(metadata),
        },
      })
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).rejects.toThrow(/expected at least 1 file entry/)
    })

    it('throws when the type has no htmlFormatLabel configured', async () => {
      context = new AncillariesContext(
        host,
        { super: { id: superTypeId } },
        sharedSecret
      )
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).rejects.toThrow(/expected at least 1 format/)
    })
  })

  describe('nameField config', () => {
    const pioneerTypeId = 'pioneer-type-id'
    const pioneerTypeDocument = {
      id: 'pioneer-type-doc-id',
      fields: [
        { name: 'pioneerName', id: 'pioneer-name-field-id' },
        { name: 'description', id: 'pioneer-desc-field-id' },
        { name: 'publicationState', id: 'pioneer-pub-state-field-id' },
      ],
      formats: [
        {
          label: 'HTML',
          id: 'pioneer-html-format-id',
          fields: [{ name: 'folder', id: 'pioneer-folder-field-id' }],
        },
      ],
    }

    const setupPioneerTypeDocumentMock = () => {
      newScope()
        .get(mockApiPath(['ancillary-types', pioneerTypeId]))
        .reply(200, pioneerTypeDocument)
    }

    it('sends the title to the configured nameField instead of name', async () => {
      context = new AncillariesContext(
        host,
        {
          pioneer: {
            id: pioneerTypeId,
            htmlFormatLabel: 'HTML',
            nameField: 'pioneerName',
          },
        },
        sharedSecret
      )
      jest.spyOn(context, 'uploadFiles').mockResolvedValue([
        {
          path: 'some/path',
          label: 'content.html',
          mimeType: 'text/html',
          dataType: 'file',
        },
      ])
      setupPioneerTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      mockfs({
        '/ancillary': {
          'metadata.json': JSON.stringify({
            ...metadata,
            ancillary_type: 'pioneer',
          }),
          'content.html': '<html></html>',
        },
      })
      const { payload } = await handleAncillary(context, '/ancillary', false)
      expect(payload.fields['pioneer-name-field-id']).toBe('My Ancillary')
    })

    it('falls back to name when no nameField is configured', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      const { payload } = await handleAncillary(context, '/ancillary', false)
      expect(payload.fields['name-field-id']).toBe('My Ancillary')
    })
  })

  describe('recategorization guard', () => {
    it('proceeds when no existing ancillary is found at the id', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryNotFound('original-id')
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).resolves.toBeDefined()
    })

    it('proceeds when the existing ancillary has the same type', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryExists('original-id', typeDocument.id)
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).resolves.toBeDefined()
    })

    it('throws when the existing ancillary has a different type', async () => {
      setupTypeDocumentMock()
      mockRawAncillaryExists('original-id', 'some-other-type-doc-id')
      await expect(
        handleAncillary(context, '/ancillary', false)
      ).rejects.toThrow(/already exists with a different type/)
    })
  })
})
