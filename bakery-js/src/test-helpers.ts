import { randomUUID } from 'crypto'
import { mkdirSync, writeFileSync, rmSync } from 'fs'
import path from 'path'
import os from 'os'

export type Files = Record<string, string | Buffer>

export class TmpFs {
  private readonly files: Files
  private readonly start: string
  private readonly tmp: string
  constructor(files: Files) {
    this.start = process.cwd()
    this.tmp = path.join(os.tmpdir(), `tmpfs-${randomUUID()}`)
    this.files = files
  }

  attach() {
    mkdirSync(this.tmp, { recursive: true })
    process.chdir(this.tmp)
    for (const [p, content] of Object.entries(this.files)) {
      const normPath = path.normalize(p)
      const dirname = path.dirname(normPath)
      if (dirname !== '.') {
        mkdirSync(dirname, { recursive: true })
      }
      writeFileSync(normPath, content)
    }
    return this
  }

  restore() {
    process.chdir(this.start)
    rmSync(this.tmp, { recursive: true })
  }
}
