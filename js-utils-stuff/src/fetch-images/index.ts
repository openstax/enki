import fetch from 'node-fetch'
import { assertTrue, assertValue } from '../utils'
import { dom, fromJSX } from '../minidom'
import { ResourceFile, XmlFile } from '../model/file'
import type { Factorio } from '../model/factorio'
import { writeFileSync } from 'fs'

export class RemoteImage {
  constructor(public readonly url: string) {}
  public get savedPath() {
    return 'notimplementedyet'
  }

  public async download() {
    const resp = await fetch(this.url)
    assertTrue(resp.ok, `ERROR: Could not fetch url='${this.url}'`)
    assertTrue(
      resp.status === 200,
      `ERROR: Expected a 200 response but got ${resp.status}. url=${this.url}`
    )
    const blob = await resp.blob()
    // TODO: Determine a filename
    writeFileSync(this.savedPath, new DataView(await blob.arrayBuffer()))
  }
}

type PageData = RemoteImage[]

export class AssembledSinglePageFile extends XmlFile<
  PageData,
  void,
  void,
  void
> {
  async parse(factorio: Factorio<void, void, void>): Promise<void> {
    const doc = dom(await this.readXml(this.readPath))
    const remoteImages = doc.map(
      '//h:img[starts-with(@src, "https://")]',
      (img) => new RemoteImage(assertValue(img.attr('href')))
    )
    this._parsed = remoteImages
  }
  protected async convert(): Promise<Node> {
    const remoteUrlMap = new Map(this.parsed.map((r) => [r.url, r]))
    const doc = dom(await this.readXml(this.readPath))
    for (const img of doc.find('//h:img[starts-with(@src, "https://")]')) {
      const url = assertValue(img.attr('src'))
      const r = assertValue(
        remoteUrlMap.get(url),
        `BUG: Could not find the image. url=${url}`
      )

      img.attr('href', this.relativeToMe(r.savedPath))
    }
    return doc.node
  }
}
