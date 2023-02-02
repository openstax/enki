import { useNamespaces } from 'xpath-ts'
import { assertTrue, assertValue, parseXml, Pos, setPos } from './utils'

type Attrs = { [key: string]: string | undefined }

/**
 * API:
 *
 * Wrap an element (or document)
 *
 * ```$doc = dom(window.document)```
 *
 * Create an element:
 *
 * ```$el = $doc.create('h:h1', {class: ['foo', 'bar']}, [child1, child2])```
 *
 * Create elements using JSX Notation:
 *
 * ```
 * $el = $doc.fromJSX(
 *      <div class="alert" disabled={isDisabled}>
 *          <ul>{items}</ul>
 *      </div>
 * )
 * ```
 *
 * Get/Set attributes/children:
 *
 * ```
 * $el.attrs = {...$el.attrs, 'data-counter': 1}
 * $el.children = []
 *```
 *
 * Add/Remove attributes:
 *
 * ```
 * $el.attr('id', 'para-1234')    // add
 * $el.attr('id', null)           // remove
 * id = $el.attr('id')            // get
 * ```
 *
 * Select existing element(s):
 *
 * ```
 * $els = $doc.find('//h:ol/h:li')           // xpath
 * $els.forEach($el => $el.remove())
 * ```
 */
export class Dom {
  constructor(public readonly node: ParentNode) {}
  public get doc() {
    return assertValue(this.node.ownerDocument)
  }
  private get el() {
    if (this.node.nodeType === this.node.ELEMENT_NODE)
      return this.node as Element
    /* istanbul ignore next */
    throw new Error('BUG: Expected node to be an element but it was not')
  }
  private get parent() {
    return assertValue(
      this.node.parentNode,
      'ERROR: This node did not have a parent'
    )
  }
  remove() {
    this.parent.removeChild(this.node)
  }
  replaceWith(newNode: Dom | JSXNode) {
    const ret =
      newNode instanceof Dom ? newNode.node : this.fromJSX(newNode).node
    this.parent.replaceChild(ret, this.node)
    return dom(ret)
  }
  /** Unset any existing attributes and set the ones provided */
  set attrs(attrs: Attrs) {
    Object.keys(this.attrs)
      .filter((v) => !Object.keys(attrs).includes(v))
      .forEach((name) => this.el.removeAttribute(name))
    Object.entries(attrs).forEach(([name, value]) =>
      this.attr(name, value as string)
    )
  }
  get attrs(): Attrs {
    return Array.from(this.el.attributes).reduce(
      (o, attr) => Object.assign(o, { [attr.name]: attr.value }),
      {}
    )
  }
  /** Get/Set/Remove a single attribute. To remove the attribute pass in `null` for the `newValue` */
  attr(name: string, newValue?: string | null) {
    const [localName, prefix] = name.split(':').reverse()
    const ns = (NAMESPACES as { [k: string]: string })[prefix]
    const old = this.el.hasAttributeNS(ns, localName)
      ? this.el.getAttributeNS(ns, localName)
      : null
    if (newValue === null) this.el.removeAttributeNS(ns, localName)
    else if (newValue !== undefined) this.el.setAttributeNS(ns, name, newValue)
    return old
  }
  get tagName() {
    return this.el.tagName
  }
  set children(children: Array<Dom | string | JSXNode>) {
    Array.from(this.node.childNodes).forEach((c) =>
      assertValue(c.parentNode).removeChild(c)
    )
    children.forEach((c) =>
      typeof c === 'string'
        ? this.node.appendChild(this.doc.createTextNode(c))
        : this.node.appendChild((c instanceof Dom ? c : this.fromJSX(c)).node)
    )
  }
  get children(): Array<Dom> {
    const a = Array.from(this.node.childNodes)
    const b = a.filter(
      (c) => c.nodeType === c.ELEMENT_NODE || c.nodeType === c.TEXT_NODE
    )
    const c = b.map((c) => dom(c as Element))
    return c
  }

  /** Creates a new element but does not attach it to the DOM.
   * Consider using fromJSX instead so that sourcemaps will
   * point to the code where the element was created
   */
  create(
    tagName: string,
    attrs: Attrs,
    children: Array<Dom | string>,
    source: Pos
  ) {
    const [tag, prefix] = tagName.split(':').reverse()
    const ns =
      prefix === undefined
        ? undefined
        : assertValue(
            (NAMESPACES as any)[prefix],
            `BUG: Unsupported namespace prefix '${prefix}'`
          )
    const el = this.doc.createElementNS(ns, tag)
    const $el = dom(el)
    if (attrs !== undefined) $el.attrs = attrs
    if (children !== undefined)
      children.forEach((c) =>
        c instanceof Dom
          ? $el.node.appendChild(c.node)
          : $el.node.appendChild(this.doc.createTextNode(c))
      )
    if (source !== undefined) setPos(el, source)
    return $el
  }

  /** Find all MiniDom nodes that match `xpath` */
  find(xpath: string) {
    const ret = this.findNodes<ParentNode>(xpath)
    return Array.from(ret, (el) => dom(el))
  }
  /** Apply `callbackfn` to every Node that matches `xpath` */
  forEach(
    xpath: string,
    callbackfn: (value: Dom, index: number, array: Dom[]) => void
  ) {
    this.find(xpath).forEach(callbackfn)
  }
  /** Apply `callbackfn` to every Node that matches `xpath` and return a new Array of type `T` */
  map<T>(
    xpath: string,
    callbackfn: (value: Dom, index: number, array: Dom[]) => T
  ): T[] {
    return this.find(xpath).map(callbackfn)
  }
  /** Check if this node contains Nodes that match `xpath` */
  has(xpath: string) {
    return this.find(xpath).length > 0
  }
  /** Find **the** one Node that matches `xpath`, otherwise error */
  findOne(xpath: string) {
    const res = this.find(xpath)
    assertTrue(
      res.length === 1,
      `ERROR: Expected to find 1 element matching the selector '${xpath}' but found ${res.length}`
    )
    return res[0]
  }
  /** Find all the dom nodes that match `xpath` */
  findNodes<T>(xpath: string) {
    return xpathSelect(xpath, this.node) as T[]
  }
  text() {
    return this.findNodes<Text>('.//text()')
      .map((n) => n.textContent)
      .join('')
  }
  /** Convert a JSX declaration to "real" DOM Nodes */
  fromJSX(j: JSXNode | string) {
    if (typeof j === 'string') return j as unknown as Dom
    assertTrue(
      !Array.isArray(j),
      'BUG: Providing an array of JSX nodes is not supported... yet!'
    )
    const source = {
      source: { fileName: j.source.fileName, content: null },
      lineNumber: j.source.lineNumber,
      columnNumber: j.source.columnNumber,
    }
    const { children, ...attrs } = j.config
    const kids: Array<Dom | string> =
      children === undefined
        ? []
        : Array.isArray(children)
        ? children.map((c) => this.fromJSX(c))
        : [this.fromJSX(children)]
    return this.create(j.tagName, attrs, kids, source)
  }
}

/** Wrap an existing Document, Element, or other Node */
export function dom(docOrEl: ParentNode) {
  return new Dom(docOrEl)
}

export const NAMESPACES = {
  c: 'http://cnx.rice.edu/cnxml',
  col: 'http://cnx.rice.edu/collxml',
  md: 'http://cnx.rice.edu/mdml',
  h: 'http://www.w3.org/1999/xhtml',
  m: 'http://www.w3.org/1998/Math/MathML',
  epub: 'http://www.idpf.org/2007/ops',
  ncx: 'http://www.daisy.org/z3986/2005/ncx/',
  opf: 'http://www.idpf.org/2007/opf',
  dc: 'http://purl.org/dc/elements/1.1/',
  books: 'https://openstax.org/namespaces/book-container',
  cont: 'urn:oasis:names:tc:opendocument:xmlns:container',
}

const xpathSelect = useNamespaces(NAMESPACES)

// Custom element attributes go here.
// If this becomes annoying then just set IntrinsicElements = any
declare global {
  namespace JSX {
    interface IntrinsicElements {
      'cont:container': { version: '1.0' }
      'cont:rootfiles': {}
      'cont:rootfile': {
        'media-type': 'application/oebps-package+xml'
        'full-path': string
      }

      'opf:package': { version: '3.0'; 'unique-identifier': string }
      'opf:metadata': {}
      'opf:meta': {
        property: 'dcterms:modified' | 'dcterms:license' | 'dcterms:alternative'
      }
      'opf:manifest': {}
      'opf:item': {
        id: string
        'media-type': string
        href: string
        properties?: string
      }
      'dc:title': {}
      'dc:language': {}
      'dc:identifier': { id: string }
      'dc:creator': {}
      'opf:spine': any
      'opf:itemref': any

      // Schema: https://github.com/w3c/epubcheck/blob/main/src/main/resources/com/adobe/epubcheck/schema/20/rng/ncx.rng
      'ncx:ncx': { version: '2005-1' }
      'ncx:head': {}
      'ncx:meta': { name: string; content: string | number }
      'ncx:docTitle': {}
      'ncx:text': {}
      'ncx:navMap': {}
      'ncx:navPoint': { id: string }
      'ncx:navLabel': {}
      'ncx:content': { src: string }

      'h:title': {}
      'h:link': { rel: 'stylesheet'; type: 'text/css'; href: string }
    }
  }
}

export type JSXNode = {
  tagName: string
  config: AttrsOrChildren
  source: SourceInfo
}
type AttrsOrChildren = { [key: string]: string | undefined } & {
  children?: JSXNode | Array<JSXNode>
}
type SourceInfo = {
  fileName: string
  lineNumber: 0
  columnNumber: 0
}
// See https://www.typescriptlang.org/tsconfig#jsx for more info
export function jsxDEV(
  tagName: string,
  config: AttrsOrChildren,
  _1: undefined,
  _2: boolean,
  source: SourceInfo
): JSXNode {
  return { tagName, config, source }
}

export function fromJSX(j: JSXNode) {
  const [tagName, prefix] = j.tagName.split(':').reverse()
  const { children, ...attrs } = j.config
  const source = {
    ...j.source,
    source: { fileName: j.source.fileName, content: null },
  }

  const doc = parseXml(
    `<${tagName} xmlns="${assertValue(
      (NAMESPACES as any)[prefix],
      `Unknown namespace prefix '${prefix}'`
    )}"/>`
  )
  setPos(doc.documentElement, source)

  const $doc = dom(doc)
  const $root = dom($doc.doc.documentElement)
  $root.attrs = attrs
  $root.children =
    children === undefined
      ? []
      : Array.isArray(children)
      ? children.map((c) => $doc.fromJSX(c))
      : [$doc.fromJSX(children)]
  return $root
}
