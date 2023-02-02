import {
    describe,
    expect,
    it,
    afterEach,
    beforeEach,
} from '@jest/globals'
import { readFileSync } from 'fs'
import mockfs from 'mock-fs'
import { factorio } from './singletons'
import { XmlFile } from '../model/file'
import { ContainerFile } from './container'

async function writeAndCheckSnapshot<T, TBook, TPage, TResource>(
    n: XmlFile<T, TBook, TPage, TResource>,
    destPath: string
) {
    n.rename(destPath, undefined)
    await n.write()
    expect(readFileSync(destPath, 'utf8')).toMatchSnapshot()
}

describe('Container File', () => {
    const containerPath = '/META-INF/books.xml'
    const destPath = '/foo/output.foo'
    const slugName = 'testslug'

    const containerContent = `<container xmlns="https://openstax.org/namespaces/book-container" version="1">
        <book slug="${slugName}" style="anystyle" />
    </container>`

    describe('with an empty book', () => {
        beforeEach(() => {
            const fs: any = {}
            fs[containerPath] = containerContent
            mockfs(fs)
        })
        afterEach(() => {
            mockfs.restore()
        })

        it('parses a simple container', async () => {
            const f = new ContainerFile(containerPath)
            await f.parse(factorio)
            await f.parse(factorio) // just for code coverage reasons to verify we only parse once
            expect(f.parsed.length).toBe(1)
            expect(f.parsed[0].readPath).toBe(`/IO_DISASSEMBLE_LINKED/${slugName}.toc.xhtml`)
            await writeAndCheckSnapshot(f, destPath)
        })
    })
})