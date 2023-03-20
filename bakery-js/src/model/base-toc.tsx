import { basename, resolve, dirname, sep, join } from 'path'
import { dom, Dom, fromJSX, JSXNode } from '../minidom'
import { assertValue, getPos, Pos } from '../utils'
import type { Factorio } from '../model/factorio'
import type { Factory, Opt } from '../model/factory'
import { XmlFile } from '../model/file'

export enum TocTreeType {
  INNER = 'INNER',
  LEAF = 'LEAF',
}
export type TocTree<TPage> =
  | {
      type: TocTreeType.INNER
      title: string
      titlePos: Pos
      children: TocTree<TPage>[]
    }
  | {
      type: TocTreeType.LEAF
      title: string
      titlePos: Pos
      page: TPage
      pagePos: Pos
    }
type TocData<TPage> = {
  toc: TocTree<TPage>[]
  allPages: Set<TPage>
}

export abstract class BaseTocFile<
  TData,
  TBook,
  TPage,
  TResource
> extends XmlFile<TData, TBook, TPage, TResource> {
  protected async baseParse(
    factorio: Factorio<TBook, TPage, TResource>
  ): Promise<TocData<TPage>> {
    const doc = dom(await this.readXml())

    const tocPages: TPage[] = []
    const toc = doc.map('//h:nav/h:ol/h:li', (el) =>
      this.buildChildren(factorio.pages, el, tocPages)
    )

    const allPages = new Set<TPage>()

    // keep looking through XHTML file links and add those to the set of allPages
    async function recPages(page: TPage) {
      /* istanbul ignore if */
      if (allPages.has(page)) return
      allPages.add(page)
    }

    for (const page of tocPages) {
      await recPages(page)
    }

    return {
      toc,
      allPages,
    }
  }
  private buildChildren(
    pageFactory: Factory<TPage>,
    li: Dom,
    acc: TPage[]
  ): TocTree<TPage> {
    // 3 options are: Subbook node, Page leaf, subbook leaf (only CNX)
    const children = li.find('h:ol/h:li')
    if (children.length > 0) {
      /* istanbul ignore next */
      const titleNode = li.has('h:a') ? li.findOne('h:a') : li.findOne('h:span')
      return {
        type: TocTreeType.INNER,
        title: titleNode.text(), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
        titlePos: getPos(titleNode.node),
        children: children.map((c) => this.buildChildren(pageFactory, c, acc)),
      }
    }
    if (li.has('h:a[not(starts-with(@href, "#"))]')) {
      const href = assertValue(
        li.findOne('h:a[not(starts-with(@href, "#"))]').attr('href')
      )
      const page = pageFactory.getOrAdd(href, this.readPath)
      acc.push(page)
      return {
        type: TocTreeType.LEAF,
        title: li.findOne('h:a').text(), //TODO: Support markup in here maybe? Like maybe we should return a DOM node?
        titlePos: getPos(li.findOne('h:a').node),
        page,
        pagePos: getPos(li.node),
      }
    }
    /* istanbul ignore next */
    throw new Error('BUG: non-page leaves are not supported yet')
  }
  public findDepth(toc: TocTree<TPage>): number {
    if (toc.type == TocTreeType.LEAF) return 1
    else
      return (
        1 +
        Math.max(
          ...toc.children.map((d) => {
            return this.findDepth(d)
          })
        )
      )
  }

  public getPagesFromToc(toc: TocTree<TPage>, acc: TPage[]) {
    if (toc.type === TocTreeType.LEAF) {
      acc.push(toc.page)
    } else {
      toc.children.forEach((c) => this.getPagesFromToc(c, acc))
    }
    return acc
  }
}
