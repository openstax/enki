import { useNamespaces } from 'xpath-ts'
import { assertTrue, assertValue } from "./utils"

type Attrs = { [key: string]: string }

/**
 * API:
 *
 * Create an element:
 *
 * ```el = dom('h:h1', {class: ['foo', 'bar']}, [child1, child2])```
 *
 * Get/Set attributes/children:
 *
 * ```
 * el.attrs = {...el.attrs, 'data-counter', 1}
 * el.children = []
 *```
 * 
 * Add/Remove attributes:
 *
 * ```
 * el.attr('id', 'para-1234')    // add
 * el.attr('id', null)           // remove
 * id = el.attr('id')            // get
 * ```
 *
 * Select existing element(s):
 *
 * ```
 * els = $$('//h:ol/h:li')           // xpath
 * els.forEach(el => el.remove())
 * ```
 */
export class Dom {
    public readonly el: Element
    constructor(docOrEl: ParentNode, tagName: string | null = null, attrs?: Attrs, children?: Array<Dom | Element | string>) {
        const doc = assertValue(docOrEl.ownerDocument ? docOrEl.ownerDocument : docOrEl as Document)
        if (typeof tagName === 'string') {
            const [tag, ns] = tagName.split(':').reverse()
            if (ns !== undefined) {
                this.el = doc.createElementNS(assertValue((NAMESPACES as any)[ns], `BUG: Unsupported namespace prefix '${ns}'`), tag)
            } else {
                this.el = doc.createElement(tag)
            }
        } else {
            this.el = docOrEl as Element
        }
        if (attrs !== undefined) this.attrs = attrs
        if (children !== undefined) children.forEach(c => c instanceof Dom ? this.el.appendChild(c.el) : typeof c === 'string' ? this.el.appendChild(doc.createTextNode(c)) : this.el.appendChild(c))
    }
    remove() { this.el.parentNode?.removeChild(this.el) }
    replaceWith(newNode: Node | Dom) { assertValue(this.el.parentNode).replaceChild(newNode instanceof Dom ? newNode.el : newNode, this.el)}
    set attrs(attrs: Attrs) {
        Object.entries(attrs).forEach(([name, value]) => this.attr(name, value as string))
    }
    get attrs(): Attrs { 
        return Array.from(this.el.attributes).reduce((o, attr) => Object.assign(o, {[attr.name]: attr.value}), {})
    }
    /** Get/Set/Remove a single attribute. To remove the attribute pass in `null` for the `newValue` */
    attr(name: string, newValue?: string | null) {
        const [localName, prefix] = name.split(':').reverse()
        const ns = (NAMESPACES as {[k: string]: string})[prefix]

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
        Array.from(this.el.childNodes).forEach(c => c.parentNode?.removeChild(c))
        children.forEach(c => typeof c === 'string' ? this.el.appendChild(this.el.ownerDocument.createTextNode(c)) : this.el.appendChild(c.el))
    }
    get children(): Array<Dom | string> {
        const a = Array.from(this.el.childNodes)
        const b = a.filter(c => c.nodeType === c.ELEMENT_NODE || c.nodeType === c.TEXT_NODE)
        const c = b.map(c => c.nodeType === c.TEXT_NODE ? assertValue(c.textContent) : dom(c as Element))
        return c
    }

    /** Creates a new element but does not attach it to the DOM */
    create(tagName: string, attrs?: Attrs, children?: Array<Dom | Element | string>) {
        const doc = assertValue(this.el.ownerDocument ? this.el.ownerDocument : this.el as unknown as Document)
        const [tag, ns] = tagName.split(':').reverse()
        const el = (ns !== undefined) ? doc.createElementNS(assertValue((NAMESPACES as any)[ns], `BUG: Unsupported namespace prefix '${ns}'`), tag) : doc.createElement(tag)
        const $el = dom(el)
        if (attrs !== undefined) $el.attrs = attrs
        if (children !== undefined) children.forEach(c => c instanceof Dom ? $el.el.appendChild(c.el) : typeof c === 'string' ? $el.el.appendChild(doc.createTextNode(c)) : $el.el.appendChild(c))
        return $el
    }

    /** Select all MiniDom nodes in `parent` that match `xpath` */
    $$(xpath: string) {
        const ret = this.$$node(xpath)
        return Array.from(ret, el => dom(el as Element))
    }
    /** Select the one MiniDom node in `parent` that matches `xpath` */
    $(xpath: string) {
        const res = this.$$(xpath)
        assertTrue(res.length === 1, `ERROR: Expected to find 1 element matching the selector '${xpath}' but found ${res.length}`)
        return res[0]
    }
    /** Select all the dom nodes in `parent` that match `xpath` */
    $$node<T>(xpath: string) {
        return xpathSelect(xpath, this.el) as T[]
    }
}

/** Create an element or wrap an existing element */
export function dom(docOrEl: ParentNode, tagName: string | null = null, attrs?: any, children?: Array<Dom | Element | string>) {
    return new Dom(docOrEl, tagName, attrs, children)
}

export const NAMESPACES = {
    c: 'http://cnx.rice.edu/cnxml',
    md: 'http://cnx.rice.edu/mdml',
    h: 'http://www.w3.org/1999/xhtml',
    m: 'http://www.w3.org/1998/Math/MathML',
    epub: 'http://www.idpf.org/2007/ops',
    ncx: 'http://www.daisy.org/z3986/2005/ncx/',
    opf: 'http://www.idpf.org/2007/opf',
    dc: 'http://purl.org/dc/elements/1.1/'
}

const xpathSelect = useNamespaces(NAMESPACES)
