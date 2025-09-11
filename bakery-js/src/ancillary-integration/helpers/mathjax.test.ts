/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-empty-function */
import { jest, describe, expect, it, beforeEach } from '@jest/globals'
import typesetMath from './mathjax'
import { SpiedFunction } from 'jest-mock'

// Mock global variables
declare global {
  interface Window {
    MathJax?: any
    __debugMathJax?: boolean
  }
}

global.window = {} as any

describe('typesetMath', () => {
  let mockWindow: any
  let setTimeoutSpy: SpiedFunction<
    ((
      callback: (...args: any[]) => void,
      ms?: number,
      ...args: any[]
    ) => NodeJS.Timeout) &
      typeof setTimeout
  >

  beforeEach(() => {
    setTimeoutSpy = jest.spyOn(global, 'setTimeout')
    setTimeoutSpy.mockImplementation((fn, _) => {
      ;(fn as () => void)()
      return 0
    })

    mockWindow = {
      MathJax: {
        Hub: {
          Config: jest.fn(),
          Configured: jest.fn(),
          Register: {
            StartupHook: jest.fn().mockImplementation((_, cb: any) => cb()),
          },
          Queue: jest.fn().mockImplementation((...callables: any[]) => {
            callables.forEach((c) => c())
          }),
          Typeset: jest.fn<() => Promise<void>>().mockResolvedValue(),
        },
        HTML: {
          Cookie: {},
        },
      },
      __debugMathJax: false,
    }
    // Clear any existing global MathJax instance
    delete window.MathJax
    global.window = mockWindow
  })

  it('should load MathJax and process math elements', async () => {
    const document = {
      createElement: jest.fn(),
      head: {} as any,
      querySelectorAll: jest.fn(),
      getElementById: jest.fn(),
    }

    const createElementSpy = jest.spyOn(document, 'createElement')

    createElementSpy.mockImplementation(() => ({
      id: '',
      src: '',
      appendChild: () => {},
      addEventListener: () => {},
    }))

    // Create a mock root element with some math content
    const mockRootElement = {
      querySelector: () => {
        return null
      },
      querySelectorAll: () => {
        return []
      },
    } as any

    // Mock document.head.appendChild
    document.head.appendChild = jest.fn()

    // Mock window.MathJax.Hub
    global.window = mockWindow
    global.document = document as any

    await typesetMath(mockRootElement)

    expect(createElementSpy).toHaveBeenCalledWith('script')
    expect(document.head.appendChild).toHaveBeenCalled()
  })

  it('should handle empty root element', async () => {
    const mockRootElement = {
      querySelector: () => mockRootElement,
      querySelectorAll: () => [],
    } as any

    setTimeoutSpy.mockImplementation(() => undefined as any)

    await typesetMath(mockRootElement, mockWindow)
    expect(setTimeoutSpy).toBeCalledTimes(0)
  })

  it('should mark processed nodes as rendered', async () => {
    const nodeFactory = (
      tagName: string,
      {
        classList,
        attributes,
      }: {
        classList?: string
        attributes?: Map<string, string>
      } = {}
    ) => {
      let className = classList ?? ''
      const attrSet = attributes ?? (new Map() as Map<string, string>)
      const node = {
        tagName,
        className,
        classList: {
          contains: (c: string) => className.indexOf(c) !== -1,
          add: (c: string) => {
            className = [...className.split(' '), c].join(' ')
          },
        },
        getAttribute(name: string) {
          return attrSet.get(name) ?? null
        },
        setAttribute(name: string, value: string) {
          attrSet.set(name, value)
        },
      }
      return node
    }
    const nodes = [
      nodeFactory('div', { attributes: new Map([['data-math', '']]) }),
      nodeFactory('math'),
    ]
    const mockRootElement = {
      querySelector: () => mockRootElement,
      querySelectorAll: (selector: string) => {
        if (selector.indexOf('data-math') !== -1) {
          const renderedMathClassMatch = /not\(.([^)]+)\)/.exec(selector)
          const renderedMathClass = renderedMathClassMatch?.[1] ?? ''
          return nodes.filter((n) => !n.classList.contains(renderedMathClass))
        } else if (selector.indexOf('.MathJax math') !== -1) {
          return []
        } else if (selector.indexOf('math') !== -1) {
          return nodes.filter((n) => n.tagName === 'math')
        } else {
          throw new Error(`Unsupported: ${selector}`)
        }
      },
    } as any

    const mathJaxHubMock = mockWindow.MathJax.Hub

    await typesetMath(mockRootElement, mockWindow)

    expect(mathJaxHubMock.Queue).toHaveBeenCalled()
  })
})
