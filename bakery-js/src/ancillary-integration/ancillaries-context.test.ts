import {
  jest,
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
} from '@jest/globals'
import {
  AncillariesContext,
  FieldConfig,
  FileInput,
  FormatConfig,
  mapFields,
  mapFormats,
} from './ancillaries-context'
import nock from 'nock'
import { assertValue } from '../utils'

describe('AncillariesContext', () => {
  const host = 'localhost'
  let context: AncillariesContext
  const newScope = () => nock(`https://${host}`)
  const superTypeId = 'super-type-id'
  const sharedSecret = 'secret'
  const mockApiPath = (path: string[], options?: { withAuth?: boolean }) => {
    const url = new URL(context.buildApiPathV0(path))
    if (options?.withAuth === true) {
      url.searchParams.set('sharedSecret', sharedSecret)
    }
    return url.href.replace(url.origin, '')
  }
  const logMessages: string[] = []

  beforeEach(() => {
    context = new AncillariesContext(
      host,
      { super: { id: superTypeId, htmlFormatLabel: 'HTML' } },
      sharedSecret
    )
    jest
      .spyOn(global, 'setTimeout')
      .mockImplementation(
        (callback) => (Promise.resolve().then(callback as () => void), 1)
      )
    logMessages.splice(0, logMessages.length)
    jest
      .spyOn(console, 'error')
      .mockImplementation((message) => logMessages.push(message))
  })

  afterEach(() => {
    nock.cleanAll()
    jest.restoreAllMocks()
  })

  it('can build urls', () => {
    expect(context.buildPath(['a', 'b', 'c'])).toMatchInlineSnapshot(
      `"https://localhost/a/b/c"`
    )
    expect(
      context.buildPath(['a', 'b', 'c'], { q: 'something', page: '1' })
    ).toMatchInlineSnapshot(`"https://localhost/a/b/c?q=something&page=1"`)
    expect(context.buildPath(['a', 'b', 'c'])).toMatchInlineSnapshot(
      `"https://localhost/a/b/c"`
    )
  })

  it('can build api urls (v0)', () => {
    expect(
      context.buildApiPathV0(['ancillaries', 'some-id'])
    ).toMatchInlineSnapshot(`"https://localhost/api/v0/ancillaries/some-id"`)
    expect(
      context.buildApiPathV0(['search'], { q: 'something' })
    ).toMatchInlineSnapshot(`"https://localhost/api/v0/search?q=something"`)
  })

  it('can fetch, retry, and fail', async () => {
    const scope = newScope()
    const mockConsoleError = jest
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)

    scope.get('/err').reply(401)
    scope.get('/err').reply(401)
    await expect(() =>
      context.fetch(`https://${host}/err`, { retries: 1 })
    ).rejects.toThrow(/^Maximum retries exceeded$/)

    // Default retries: 2
    scope.get('/err').reply(401)
    scope.get('/err').reply(401)
    scope.get('/err').reply(401)
    await expect(() => context.fetch(`https://${host}/err`)).rejects.toThrow(
      /^Maximum retries exceeded$/
    )

    scope.get('/err').reply(401)
    await expect(() =>
      context.fetch(`https://${host}/err`, { accept: [200], retries: 0 })
    ).rejects.toThrow(/^Maximum retries exceeded$/)

    expect(mockConsoleError).toHaveBeenCalledTimes(6)
    expect(mockConsoleError.mock.calls).toMatchInlineSnapshot(`
      [
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
        [
          [Error: 401: Unauthorized
      Body: ],
        ],
      ]
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can build type configs and get type', async () => {
    const scope = newScope()
    const url = mockApiPath(['ancillary-types', superTypeId], {
      withAuth: true,
    })
    scope.get(url).reply(200, { 'mocked-response': 'true' })

    const ancillaryTypeConfig = context.ancillaryTypesByName
    expect(Object.keys(ancillaryTypeConfig)).toMatchInlineSnapshot(`
      [
        "super",
      ]
    `)
    const superConfig = assertValue(ancillaryTypeConfig['super'])
    expect(await superConfig.typeDocument).toMatchInlineSnapshot(`
      {
        "mocked-response": "true",
      }
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can get upload config', async () => {
    const scope = newScope()
    const url = mockApiPath(['files', 'authorize-upload'], { withAuth: true })
    scope.get(url).reply(200, {
      'not-a-real-response': 'true',
    })
    expect(await context.authorizeUpload()).toMatchInlineSnapshot(`
      {
        "not-a-real-response": "true",
      }
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can upload a file', async () => {
    const fakeUploadPath = '/upload'
    const uploadConfig = {
      url: `https://${host}${fakeUploadPath}`,
      payload: {
        key: 'a/path/to/a/${filename}',
        super: '1',
        cool: '2',
        payload: '3',
        object: '4',
      },
    }
    const file: FileInput = {
      blob: Buffer.from(''),
      name: 'file',
      type: 'fake',
    }
    const scope = newScope()
    scope.post(fakeUploadPath).reply(200)
    const result = await context.uploadFile(file, uploadConfig)
    expect(result).toMatchInlineSnapshot(`
      {
        "dataType": "file",
        "label": "file",
        "mimeType": "fake",
        "path": "a/path/to/a/file",
      }
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can upload multiple files', async () => {
    const scope = newScope()
    const url = mockApiPath(['files', 'authorize-upload'], { withAuth: true })
    const fakeUploadPath = '/upload'
    const uploadConfig = {
      url: `https://${host}${fakeUploadPath}`,
      payload: {
        key: 'a/path/to/a/${filename}',
        super: '1',
        cool: '2',
        payload: '3',
        object: '4',
      },
    }
    const files: FileInput[] = [
      {
        blob: Buffer.from(''),
        name: 'file',
        type: 'fake',
      },
      {
        blob: Buffer.from(''),
        name: 'file2',
        type: 'fake',
      },
    ]
    scope.get(url).reply(200, uploadConfig)
    files.forEach(() => {
      scope.post(fakeUploadPath).reply(200)
    })
    const result = await context.uploadFiles(files)
    expect(result).toMatchInlineSnapshot(`
      [
        {
          "dataType": "file",
          "label": "file",
          "mimeType": "fake",
          "path": "a/path/to/a/file",
        },
        {
          "dataType": "file",
          "label": "file2",
          "mimeType": "fake",
          "path": "a/path/to/a/file2",
        },
      ]
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('handles exactly 10 files correctly', async () => {
    const scope = newScope()
    const fakeUploadPath = '/upload'
    const uploadConfig = {
      url: `https://${host}${fakeUploadPath}`,
      payload: {
        key: 'a/path/to/a/${filename}',
        super: '1',
        cool: '2',
        payload: '3',
        object: '4',
      },
    }

    const tenFiles: FileInput[] = Array.from({ length: 10 }, (_, i) => ({
      blob: Buffer.from(`file${i}`),
      name: `file${i}`,
      type: 'text/plain',
    }))

    // Mock the GET request to authorize upload
    scope
      .get(mockApiPath(['files', 'authorize-upload'], { withAuth: true }))
      .reply(200, uploadConfig)

    // Mock POST requests for each file
    tenFiles.forEach(() =>
      scope
        .post(fakeUploadPath)
        .matchHeader('content-type', /multipart\/form-data/)
        .reply(200)
    )

    const result = await context.uploadFiles(tenFiles)

    expect(result.length).toBe(10)
    expect(scope.isDone()).toBe(true)
  })

  it('handles more than 10 files correctly', async () => {
    const scope = newScope()
    const fakeUploadPath = '/upload'

    const twentyOneFiles: FileInput[] = Array.from({ length: 21 }, (_, i) => ({
      blob: Buffer.from(`file${i}`),
      name: `file${i}`,
      type: 'text/plain',
    }))

    // Mock the GET request to authorize upload
    scope
      .get(mockApiPath(['files', 'authorize-upload'], { withAuth: true }))
      .reply(200, {
        url: `https://${host}${fakeUploadPath}`,
        payload: {
          key: 'a/path/to/a/${filename}',
        },
      })

    // Mock POST requests for each chunk of 10 files
    for (let i = 0; i < Math.ceil(twentyOneFiles.length / 10); i++) {
      const chunk = twentyOneFiles.slice(i * 10, (i + 1) * 10)
      chunk.forEach(() =>
        scope
          .post(fakeUploadPath)
          .matchHeader('content-type', /multipart\/form-data/)
          .reply(200)
      )
    }

    const result = await context.uploadFiles(twentyOneFiles)

    expect(result.length).toBe(21)
    expect(scope.isDone()).toBe(true)
  })

  it('handles empty files array', async () => {
    const scope = newScope()

    const result = await context.uploadFiles([])

    expect(result).toMatchInlineSnapshot(`[]`)
    expect(scope.isDone()).toBe(true)
  })

  it('handles empty files correctly', async () => {
    const scope = newScope()
    const fakeUploadPath = '/upload'

    const emptyFiles: FileInput[] = [
      {
        blob: Buffer.from(''),
        name: 'empty',
        type: 'text/plain',
      },
      {
        blob: Buffer.from(''),
        name: 'anotherEmpty',
        type: 'text/plain',
      },
    ]

    scope
      .get(mockApiPath(['files', 'authorize-upload'], { withAuth: true }))
      .reply(200, {
        url: `https://${host}${fakeUploadPath}`,
        payload: {
          key: 'a/path/to/a/${filename}',
        },
      })

    emptyFiles.forEach(() =>
      scope
        .post(fakeUploadPath)
        .matchHeader('content-type', /multipart\/form-data/)
        .reply(200)
    )

    const result = await context.uploadFiles(emptyFiles)

    expect(result.length).toBe(2)
    expect(scope.isDone()).toBe(true)
  })

  it('can write ancillaries', async () => {
    const id = '0'
    const url = mockApiPath(['ancillaries', id], { withAuth: true })
    const scope = newScope()
    scope.post(url).reply(200, { 'mock-response': 'true' })

    const result = await context.writeAncillary(
      id,
      JSON.stringify({ hey: 'imanancillary' })
    )
    expect(await result.json()).toMatchInlineSnapshot(`
      {
        "mock-response": "true",
      }
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can get compiled ancillaries', async () => {
    const id = '0'
    const url = mockApiPath(['ancillaries', id, 'compiled'])
    const scope = newScope()
    scope.get(url).reply(200, { 'mock-response': 'true' })

    const result = await context.getCompiled(id)
    expect(await result).toMatchInlineSnapshot(`
      {
        "mock-response": "true",
      }
    `)
    expect(scope.isDone()).toBe(true)
  })

  it('can be created from env', () => {
    process.env.ANCILLARIES_HOST = ''
    process.env.ANCILLARY_TYPE_CONFIG = JSON.stringify({})
    process.env.ANCILLARIES_SHARED_SECRET = ''

    const context = AncillariesContext.fromEnv()
    expect(context).toBeDefined()
  })
})

describe('mapFields', () => {
  it('maps fields correctly with matching names and IDs', () => {
    const inputFields = { foo: 'fooValue', bar: 'barValue' }
    const fieldConfigs = [
      { name: 'foo', id: 'fooId' },
      { name: 'bar', id: 'barId' },
    ]

    const result = mapFields(inputFields, fieldConfigs)

    expect(result).toEqual({
      fooId: 'fooValue',
      barId: 'barValue',
    })
  })

  it('ignores fields without corresponding configs', () => {
    const inputFields = { foo: 'fooValue', bar: 'barValue', baz: 'bazValue' }
    const fieldConfigs = [
      { name: 'foo', id: 'fooId' },
      { name: 'bar', id: 'barId' },
    ]

    const result = mapFields(inputFields, fieldConfigs)

    expect(result).not.toHaveProperty('baz')
  })

  it('returns empty object when no matching configs are found', () => {
    const inputFields = { foo: 'fooValue', bar: 'barValue' }
    const fieldConfigs: FieldConfig[] = []

    const result = mapFields(inputFields, fieldConfigs)

    expect(result).toEqual({})
  })
})

describe('mapFormats', () => {
  it('maps formats correctly with matching labels and IDs', () => {
    const inputFormats = {
      format1: { foo: 'fooValue', bar: 'barValue' },
      format2: { baz: 'bazValue' },
    }
    const formatConfigs = [
      {
        label: 'format1',
        id: 'format1Id',
        fields: [
          { name: 'foo', id: 'fooId' },
          { name: 'bar', id: 'barId' },
        ],
      },
      {
        label: 'format2',
        id: 'format2Id',
        fields: [{ name: 'baz', id: 'bazId' }],
      },
    ]

    const result = mapFormats(inputFormats, formatConfigs)

    expect(result).toEqual({
      format1Id: {
        fields: { fooId: 'fooValue', barId: 'barValue' },
      },
      format2Id: {
        fields: { bazId: 'bazValue' },
      },
    })
  })

  it('ignores formats without corresponding configs', () => {
    const inputFormats = {
      format1: { foo: 'fooValue' },
      format3: { unknown: 'unknownValue' },
    }
    const formatConfigs = [
      {
        label: 'format1',
        id: 'format1Id',
        fields: [{ name: 'foo', id: 'fooId' }],
      },
    ]

    const result = mapFormats(inputFormats, formatConfigs)

    expect(result).not.toHaveProperty('format3')
  })

  it('handles empty formats and configs appropriately', () => {
    const inputFormats = {}
    const formatConfigs: FormatConfig[] = []

    const result = mapFormats(inputFormats, formatConfigs)

    expect(result).toEqual({})
  })
})
