// From https://github.com/philschatz/stylish/blob/3eb109d86d74ad910ca9fa6f393579c3087aefbe/src/enki-replacement/utils.ts
import { readFileSync, writeFileSync, WriteStream, createWriteStream } from 'fs'
import { dirname, relative, resolve } from 'path'
import { SourceMapConsumer, SourceMapGenerator } from 'source-map'
import { DOMParser } from 'xmldom'
import { useNamespaces } from 'xpath-ts'

class ParseError extends Error { }

export type Pos = {
    source: FileInfo
    lineNumber: number
    columnNumber: number
}

export type FileInfo = {
    filename: string
    content: string | null
}

export function assertTrue(v: boolean, message = 'Expected to be true') {
    if (v !== true) {
        debugger
        throw new Error(message)
    }
}
export function assertValue<T>(v: T | null | undefined, message: string = 'Expected a value but did not get anything') {
    if (v !== null && v !== undefined) return v
    debugger
    throw new Error(`BUG: assertValue. Message: ${message}`)
}

// xmldom parser includes the line/column information on the Node (but it's not exposed in the public API)
function getPos(node: Node): Pos {
    return node as unknown as Pos
}
function setPos(node: Node, p: Pos) {
    const n = node as unknown as Pos
    n.columnNumber = p.columnNumber
    n.lineNumber = p.lineNumber
    n.source = p.source
}

function visit(n: Node, visitor: (n: Node) => void) {
    visitor(n)
    for (const c of Array.from(n.childNodes || [])) {
        visit(c, visitor)
    }
    const attrs = (n as any).attributes
    for (const attr of Array.from(attrs || [])) {
        visitor(attr as Node)
    }
}

function parseXml(fileContent: string, _filename: string) {
    const locator = { lineNumber: 0, columnNumber: 0 }
    const cb = () => {
        const pos = {
            line: locator.lineNumber - 1,
            character: locator.columnNumber - 1
        }
        throw new ParseError(`ParseError: ${JSON.stringify(pos)}`)
    }
    const p = new DOMParser({
        locator,
        errorHandler: {
            warning: console.warn,
            error: cb,
            fatalError: cb
        }
    })
    const doc = p.parseFromString(fileContent)
    return doc
}

// https://github.com/xmldom/xmldom/blob/5eb649e00aeaaf016cad313f12ef0da02b563a1f/lib/dom.js#L544-L550
function _xmlEncoder(c: string){
	return c == '<' && '&lt;' ||
         c == '>' && '&gt;' ||
         c == '&' && '&amp;' ||
         c == '"' && '&quot;' ||
         '&#'+c.charCodeAt(0)+';'
}

// https://github.com/xmldom/xmldom/blob/5eb649e00aeaaf016cad313f12ef0da02b563a1f/lib/dom.js#L1179-L1194
function escapeAttribute(v: string) {
    return v.replace(/[<>&"\t\n\r]/g, _xmlEncoder)
}

// https://github.com/xmldom/xmldom/blob/5eb649e00aeaaf016cad313f12ef0da02b563a1f/lib/dom.js#L1324-L1342
function escapeText(v: string) {
    return v.replace(/[<&>]/g,_xmlEncoder)
}


class XMLSerializer {
    private w: SourceMapWriter
    constructor(private outputFile: string, private root: Node, private format: XmlFormat) {
        this.outputFile = resolve(this.outputFile)
        this.w = new SourceMapWriter(outputFile)
    }
    public writeFiles() {
        const sourcemapFile = `${this.outputFile}.map`
        this.recWrite(this.root)
        this.w.finish(sourcemapFile)
    }

    private recWrite(n: Node) {
        if (n.nodeType === n.DOCUMENT_NODE) {
            const doc = n as Document
            this.recWrite(doc.documentElement)
    
        } else if (n.nodeType === n.TEXT_NODE) {
            const textNode = n as Text
            this.w.writeText(n, escapeText(textNode.data))
    
        } else if (n.nodeType === n.COMMENT_NODE) {
            const comment = n as Comment
            this.w.writeText(n, `<!--${escapeText(comment.data)}-->`)
    
        } else if (n.nodeType === n.ATTRIBUTE_NODE) {
            this.w.writeText(n, ` ${n.nodeName}="${escapeAttribute(n.nodeValue || '')}"`)
    
        } else if (n.nodeType === n.ELEMENT_NODE) {
            const el = n as Element
            const prefixedTag = el.tagName
            const localTag = el.tagName
            this.w.writeText(n, `<${prefixedTag}`)
            for (const attr of Array.from(el.attributes)) {
                this.recWrite(attr)
            }
            if (isSelfClosing(this.format, localTag, el.namespaceURI)) {
                assertTrue(el.childElementCount === 0)
                this.w.writeText(n, '/>')
            } else if (el.childElementCount === 0) {
                this.w.writeText(n, '/>')
            } else {
                this.w.writeText(n, '>')
                for (const child of Array.from(el.childNodes)) {
                    this.recWrite(child)
                }
                this.w.writeText(n, `</${prefixedTag}>`)
            }
        } else {
            assertTrue(false, 'BUG: Unsupported node type for now. Just add another case here')
        }
    }
}


export enum XmlFormat {
    XML,
    XHTML5,
}

const Xhtml5EmptyTagNames = new Set([
    "area", "base", "br", "col", /*"command",*/ "embed", "hr", "img", "input", "keygen", "link", "meta", "param",
    "source", "track", "wbr"
])

function isSelfClosing(format: XmlFormat, tagName: string, ns: string | null) {
    return format === XmlFormat.XHTML5 && ns === 'http://www.w3.org/1999/xhtml' && Xhtml5EmptyTagNames.has(tagName)
}

class SourceMapWriter {
    private fileWriter: WriteStream
    private readonly g = new SourceMapGenerator()
    private readonly sources = new Map<string, string | null>()
    private currentLine = 1
    private currentCol = 0
    private absToRelativeSources = new Map<string, string>() // absolute path -> relative path

    constructor(private outputFile: string) {
        this.outputFile = resolve(outputFile)
        this.fileWriter = createWriteStream(outputFile)
    }

    relativeToOutputFile(sourceFile: string) {
        return relative(this.outputFile, sourceFile)
    }

    writeText(sourceNode: Node, text: string | null) {
        if (text === null) return

        // Add the source file if it has not been added yet
        const pos = getPos(sourceNode)
        if (pos.source) {
            if (!this.absToRelativeSources.has(pos.source.filename)) {
                this.absToRelativeSources.set(pos.source.filename, relative(dirname(this.outputFile), pos.source.filename))
            }
            const filename = assertValue(this.absToRelativeSources.get(pos.source.filename))
            if (!this.sources.has(filename)) {
                this.sources.set(filename, pos.source.content)
            }
    
            this.g.addMapping({
                source: filename,
                original: { line: pos.lineNumber, column: pos.columnNumber },
                generated: { line: this.currentLine, column: this.currentCol }
            })
        } else {
            this.g.addMapping({
                source: '(frominsidethecode)',
                original: { line: 1, column: 0 },
                generated: { line: this.currentLine, column: this.currentCol }
            })
        }
        // Append the first line
        const lines = text.split('\n')
        const first = lines.shift()
        if (first) {
            this.currentCol += first.length
        }
        // Add a new line for each line
        for (const line of lines) {
            this.currentLine++
            this.currentCol = line.length
        }
        this.fileWriter.write(text)
    }

    finish(sourcemapFile: string | null) {
        const s = assertValue(sourcemapFile, 'inline sourcemaps are not supported yet but they are very easy to add. Just use a dataURI & base64 encodethe file')
        this.fileWriter.write(`\n<!-- # sourceMappingURL=${relative(dirname(this.outputFile), s)} -->`)
        this.fileWriter.close()

        for (const [sourceFile, sourceContent] of Array.from(this.sources.entries())) {
            if (sourceContent !== null) {
                this.g.setSourceContent(sourceFile, sourceContent)
            }
        }
        writeFileSync(s, this.g.toString())
    }
}


export async function readXmlWithSourcemap(filename: string) {
    filename = resolve(filename) // make absolute for sourcemaps
    const fileContent = readFileSync(filename, 'utf-8')
    const doc = parseXml(fileContent, filename)

    // Add the source file info to every node
    visit(doc.documentElement, n => {
        (n as unknown as Pos).source = { filename, content: fileContent }
    })

    // If there is a sourcemap reference at the bottom of the XML file then load the sourcemap and rewrite the references on the nodes
    const lastChild = assertValue(doc.lastChild)
    if (lastChild.nodeType === lastChild.COMMENT_NODE) {
        const comment = lastChild as Comment
        const i = comment.data.indexOf('sourceMappingURL=')
        if (i >= 0) {
            const sourcemapFile = comment.data.substring(i + 'sourceMappingURL='.length).trim()
            // We have a SourceMap!
            const sourceMap = JSON.parse(readFileSync(resolve(dirname(filename), sourcemapFile), 'utf-8'))
            await SourceMapConsumer.with(sourceMap, null, (c) => {
                const sourcesMap = new Map<string, FileInfo>()
                c.sources.forEach(s => {
                    const abs = resolve(dirname(filename), s)
                    sourcesMap.set(abs, {
                        filename: abs,
                        content: c.sourceContentFor(s)
                    })
                })

                visit(doc.documentElement, (n) => {
                    const pos = getPos(n)
                    const mappedPos = c.originalPositionFor({
                        line: pos.lineNumber,
                        column: pos.columnNumber
                    })
                    const abs = resolve(dirname(filename), assertValue(mappedPos.source, 'BUG'))
                    const source = assertValue(sourcesMap.get(abs), 'Extra buggy. Fix this')
                    setPos(n, {
                        lineNumber: assertValue(mappedPos.line, 'BUG: Need to handle this case'),
                        columnNumber: assertValue(mappedPos.column, 'BUG: Need to handle this case'),
                        source: source
                    })
                })
            })
        }
    }

    return doc
}

export function writeXmlWithSourcemap(filename: string, root: Node, xmlFormat: XmlFormat) {
    const w = new XMLSerializer(filename, root, xmlFormat)
    w.writeFiles()
}























const NAMESPACES = {
    'c': 'http://cnx.rice.edu/cnxml',
    'md': 'http://cnx.rice.edu/mdml',
    'h': 'http://www.w3.org/1999/xhtml',
    'm': 'http://www.w3.org/1998/Math/MathML'
}

const select = useNamespaces(NAMESPACES)

export function selectAll<T>(xpath: string, node: Node) {
    const res = select(xpath, node)
    if (Array.isArray(res)) {
        return res as T[]
    } else {
        return [res] as T[]
    }
}
export function selectOne<T>(xpath: string, node: Node) {
    const res = select(xpath, node)
    if (Array.isArray(res)) {
        assertTrue(res.length === 1)
        return res[0] as T
    } else {
        return res as T
    }
}

