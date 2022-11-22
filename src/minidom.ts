import { useNamespaces } from 'xpath-ts'
import { assertTrue, assertValue } from "./utils"

type Attrs = { [key: string]: string }

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
    constructor(public readonly node: ParentNode) { }
    private get doc() {
        const { ownerDocument } = this.node
        return ownerDocument !== null ? ownerDocument : this.node as unknown as Document
    }
    private get el() {
        if (this.node.nodeType === this.node.ELEMENT_NODE) return this.node as Element
        throw new Error('BUG: Expected node to be an element but it was not')
    }
    remove() { this.node.parentNode?.removeChild(this.node) }
    replaceWith(newNode: Node | Dom) { assertValue(this.node.parentNode).replaceChild(newNode instanceof Dom ? newNode.node : newNode, this.node) }
    set attrs(attrs: Attrs) {
        Object.entries(attrs).forEach(([name, value]) => this.attr(name, value as string))
    }
    get attrs(): Attrs {
        return Array.from(this.el.attributes).reduce((o, attr) => Object.assign(o, { [attr.name]: attr.value }), {})
    }
    /** Get/Set/Remove a single attribute. To remove the attribute pass in `null` for the `newValue` */
    attr(name: string, newValue?: string | null) {
        const [localName, prefix] = name.split(':').reverse()
        const ns = (NAMESPACES as { [k: string]: string })[prefix]
        const old = this.el.getAttributeNS(ns, localName)
        if (newValue === null) this.el.removeAttributeNS(ns, localName)
        else if (newValue !== undefined) this.el.setAttributeNS(ns, name, newValue)
        return old
    }
    get tagName() { return this.el.tagName }
    addClass(cls: string) { this.el.classList.add(cls) }
    removeClass(cls: string) { this.el.classList.remove(cls) }
    get classes() { return new Set(Array.from(this.el.classList)) }
    set children(children: Array<Dom | string>) {
        Array.from(this.node.childNodes).forEach(c => c.parentNode?.removeChild(c))
        children.forEach(c => typeof c === 'string' ? this.node.appendChild(this.doc.createTextNode(c)) : this.node.appendChild(c.node))
    }
    get children(): Array<Dom | string> {
        const a = Array.from(this.node.childNodes)
        const b = a.filter(c => c.nodeType === c.ELEMENT_NODE || c.nodeType === c.TEXT_NODE)
        const c = b.map(c => c.nodeType === c.TEXT_NODE ? assertValue(c.textContent) : dom(c as Element))
        return c
    }

    /** Creates a new element but does not attach it to the DOM */
    create(tagName: string, attrs?: Attrs, children?: Array<Dom | Element | string>) {
        const [tag, ns] = tagName.split(':').reverse()
        const el = (ns !== undefined) ? this.doc.createElementNS(assertValue((NAMESPACES as any)[ns], `BUG: Unsupported namespace prefix '${ns}'`), tag) : this.doc.createElement(tag)
        const $el = dom(el)
        if (attrs !== undefined) $el.attrs = attrs
        if (children !== undefined) children.forEach(c => c instanceof Dom ? $el.node.appendChild(c.node) : typeof c === 'string' ? $el.node.appendChild(this.doc.createTextNode(c)) : $el.node.appendChild(c))
        return $el
    }

    /** Find all MiniDom nodes that match `xpath` */
    find(xpath: string) {
        const ret = this.findNodes<ParentNode>(xpath)
        return Array.from(ret, el => dom(el))
    }
    /** Apply `callbackfn` to every Node that matches `xpath` */
    forEach(xpath: string, callbackfn: (value: Dom, index: number, array: Dom[]) => void) { this.find(xpath).forEach(callbackfn) }
    /** Apply `callbackfn` to every Node that matches `xpath` and return a new Array of type `T` */
    map<T>(xpath: string, callbackfn: (value: Dom, index: number, array: Dom[]) => T): T[] { return this.find(xpath).map(callbackfn) }
    /** Check if this node contains Nodes that match `xpath` */
    has(xpath: string) { return this.find(xpath).length > 0 }
    /** Find **the** one Node that matches `xpath`, otherwise error */
    findOne(xpath: string) {
        const res = this.find(xpath)
        assertTrue(res.length === 1, `ERROR: Expected to find 1 element matching the selector '${xpath}' but found ${res.length}`)
        return res[0]
    }
    /** Find all the dom nodes that match `xpath` */
    findNodes<T>(xpath: string) {
        return xpathSelect(xpath, this.node) as T[]
    }
}

/** Wrap an existing Document, Element, or other Node */
export function dom(docOrEl: ParentNode) {
    return new Dom(docOrEl)
}

export const NAMESPACES = {
    c: 'http://cnx.rice.edu/cnxml',
    md: 'http://cnx.rice.edu/mdml',
    h: 'http://www.w3.org/1999/xhtml',
    m: 'http://www.w3.org/1998/Math/MathML',
    epub: 'http://www.idpf.org/2007/ops',
    ncx: 'http://www.daisy.org/z3986/2005/ncx/',
    opf: 'http://www.idpf.org/2007/opf',
    dc: 'http://purl.org/dc/elements/1.1/',
    books: 'https://openstax.org/namespaces/book-container',
    cont: 'urn:oasis:names:tc:opendocument:xmlns:container'
}

const xpathSelect = useNamespaces(NAMESPACES)
