import {
  acceptStatus,
  getMimeType,
  hadUnexpectedError,
  listDirectory,
  mimetypeByExtension,
} from './utils'
import * as fs from 'fs'
import {
  jest,
  describe,
  expect,
  it,
  afterEach,
  beforeEach,
  beforeAll,
  test,
} from '@jest/globals'
import { mockfs } from '../mock-fs'
import { FieldConfig, FormatConfig } from './ancillaries-context'

const fail = (message: string) => {
  throw new Error(message)
}

// Mocking the required modules
jest.mock('fs')

describe('getMimeType', () => {
  // Setup mock for the mime type map
  // const originalMimeMap = mimetypeByExtension
  const mockMimeMap = new Map()
  const logMessages: string[] = []

  beforeAll(() => {
    jest.clearAllMocks()
    // Setup some sample mime types in the mock map
    mockMimeMap.set('.pdf', 'application/pdf')
    mockMimeMap.set('.png', 'image/png')
    mockMimeMap.set('.txt', 'text/plain')
  })

  beforeEach(() => {
    jest.clearAllMocks()
    jest
      .spyOn(mimetypeByExtension, 'get')
      .mockImplementation((ext) => mockMimeMap.get(ext))
    logMessages.splice(0, logMessages.length)
    jest
      .spyOn(console, 'error')
      .mockImplementation((message) => logMessages.push(message))
  })

  afterEach(() => {
    mockfs.restore()
  })

  it('should return mime type based on file extension', () => {
    expect(getMimeType('document.pdf')).toBe('application/pdf')
    expect(getMimeType('image.png')).toBe('image/png')
    expect(getMimeType('text.txt')).toBe('text/plain')
  })

  it('should return undefined when no mime type is found in the map and no metadata file exists', () => {
    expect(getMimeType('unknown.xyz')).toBe(undefined)
  })

  it('should check for metadata file when no mime type is found by extension', () => {
    mockfs({
      'movie.mp4.json': JSON.stringify({
        mime_type: 'video/mp4',
      }),
    })

    expect(getMimeType('movie.mp4')).toBe('video/mp4')
    expect(fs.existsSync).toHaveBeenCalledWith('movie.mp4.json')
    expect(fs.readFileSync).toHaveBeenCalled()
  })

  it('should handle non-existent metadata file gracefully', () => {
    mockfs({})

    expect(getMimeType('test.xyz')).toBe(undefined)
    expect(fs.existsSync).toHaveBeenCalledWith('test.xyz.json')
    expect(fs.readFileSync).not.toHaveBeenCalled()
  })

  it('should handle invalid JSON in metadata file', () => {
    mockfs({
      'corrupted.xyz.json': '{invalid json, yo}',
    })

    expect(getMimeType('corrupted.xyz')).toBe(undefined)
  })

  it('should handle empty metadata file', () => {
    mockfs({
      'empty.xyz.json': JSON.stringify({}),
    })

    expect(getMimeType('empty.xyz')).toBe(undefined)
  })
})

describe('hadUnexpectedError', () => {
  it('should return true when status is not in accepted array', () => {
    expect(hadUnexpectedError({ status: 404 }, [200, 201])).toBe(true)
    expect(hadUnexpectedError({ status: 500 }, [200, 201])).toBe(true)
    expect(hadUnexpectedError({ status: 403 }, [200, 201, 401])).toBe(true)
  })

  it('should return false when status is in accepted array', () => {
    expect(hadUnexpectedError({ status: 200 }, [200, 201])).toBe(false)
    expect(hadUnexpectedError({ status: 401 }, [200, 201, 401])).toBe(false)
    expect(hadUnexpectedError({ status: 201 }, [200, 201, 401])).toBe(false)
  })

  it('should handle empty accepted array', () => {
    expect(hadUnexpectedError({ status: 200 }, [])).toBe(true)
  })
})

describe('acceptStatus', () => {
  let mockResponse: Response

  beforeEach(() => {
    mockResponse = new Response('', {
      status: 500,
      statusText: 'Internal Server Error',
    })
  })

  it('should throw when unexpected status is encountered', async () => {
    await expect(acceptStatus(mockResponse, [200, 201])).rejects
      .toMatchInlineSnapshot(`
      [Error: 500: Internal Server Error
      Body: ]
    `)

    // Verify body was consumed
    expect(mockResponse.bodyUsed).toBe(true)
  })

  it('should include full response details in error message', async () => {
    mockResponse = new Response('{"error": "something went wrong"}', {
      status: 400,
      statusText: 'Bad Request',
    })

    await expect(acceptStatus(mockResponse, [200])).rejects
      .toMatchInlineSnapshot(`
      [Error: 400: Bad Request
      Body: {"error": "something went wrong"}]
    `)
  })

  it('should not throw for accepted statuses', async () => {
    const response = new Response('', { status: 200, statusText: 'OK' })
    const result = await acceptStatus(response, [200])
    expect(result.status).toBe(200) // Make sure we got back the original response
  })

  it('should properly handle large responses', async () => {
    const largeBody = 'x'.repeat(1500)
    mockResponse = new Response(largeBody, {
      status: 500,
      statusText: 'Internal Server Error',
    })

    try {
      await acceptStatus(mockResponse, [200])
      fail('Expected function to reject')
    } catch (error: any) {
      expect(error.message).toContain(largeBody.substring(0, 100)) // truncated for brevity
      expect(error.message.length).toBeLessThanOrEqual(1000 + 60) // assuming some fixed overhead
    }
  })
})

describe('listDirectory', () => {
  beforeEach(() => {
    mockfs({
      '/': {
        root: {
          dir1: {
            subDir1: {},
            file1: 'content',
            file2: 'more content',
          },
          dir2: {
            file3: 'even more content',
          },
          file4: 'last file',
        },
      },
    })
  })

  afterEach(() => {
    mockfs.restore()
  })

  it('should list files and directories recursively', () => {
    const result = listDirectory('/root')

    expect(result.root).toBe('/root')
    expect(result.listing).toMatchInlineSnapshot(`
      [
        {
          "relPath": "dir1",
          "type": "directory",
        },
        {
          "relPath": "dir1/subDir1",
          "type": "directory",
        },
        {
          "relPath": "dir1/file1",
          "type": "file",
        },
        {
          "relPath": "dir1/file2",
          "type": "file",
        },
        {
          "relPath": "dir2",
          "type": "directory",
        },
        {
          "relPath": "dir2/file3",
          "type": "file",
        },
        {
          "relPath": "file4",
          "type": "file",
        },
      ]
    `)
  })

  it('should handle empty directories', () => {
    const result = listDirectory('/root/dir1/subDir1') // empty directory

    expect(result.listing.length).toBe(0)
  })

  it('should work with non-existent directories (throw error)', () => {
    expect(() => {
      listDirectory('/nonexistent/directory')
    }).toThrow()
  })
})
