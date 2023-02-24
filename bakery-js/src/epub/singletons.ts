import { Factorio } from '../model/factorio'
import { ResourceFile } from '../model/file'
import { PageFile } from './page'
import { OpfFile } from './toc'

export const factorio: Factorio<OpfFile, PageFile, ResourceFile> = new Factorio(
  (absPath) => new OpfFile(absPath),
  (absPath) => new PageFile(absPath),
  (absPath) => new ResourceFile(absPath)
)
