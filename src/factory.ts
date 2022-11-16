import { dirname, join } from "path"

export type Opt<T> = T | undefined

// Inspired by the Factory in POET
export class Factory<T> {
  private readonly _map = new Map<string, T>()
  constructor(private readonly builder: (filePath: string) => T, private readonly canonicalizer: (filePath: string) => string) { }
  get(relPath: string, relTo: Opt<string>): Opt<T> {
    const absPath = this.canonicalizer(relTo === undefined ? relPath : join(dirname(relTo), relPath))
    return this._map.get(absPath)
  }
  getOrAdd(relPath: string, relTo: Opt<string>) {
    const absPath = this.canonicalizer(relTo === undefined ? relPath : join(dirname(relTo), relPath))
    const v = this._map.get(absPath)
    if (v !== undefined) {
      return v
    } else {
      const n = this.builder(absPath)
      this._map.set(absPath, n)
      return n
    }
  }

  public remove(absPath: string) {
    absPath = this.canonicalizer(absPath)
    const item = this._map.get(absPath)
    this._map.delete(absPath)
    return item
  }
  public get size() { return this._map.size }
  public get all() { return this._map.values() }
}