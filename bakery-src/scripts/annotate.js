const fs = require('fs')
const path = require('path')
const sax = require('sax')

const XML_ENTITIES = {
  '<': '&lt;',
  '>': '&gt;',
  '&': '&amp;',
  '\'': '&apos;',
  '"': '&quot;',
}
const escapeXml = (unsafe) => unsafe.replace(/[<>&'"]/g, c => XML_ENTITIES[c])

function* walk (start = '.') {
  const toVisit = [start]
  while (toVisit.length) {
    const cwd = toVisit.shift()
    for (const dirent of fs.readdirSync(cwd, { withFileTypes: true })) {
      const pathEntry = {
        dirent,
        parent: cwd,
        get path() {
          return `${this.parent}/${this.dirent.name}`
        }
      }
      if (dirent.isDirectory()) {
        toVisit.push(pathEntry.path)
      }
      yield pathEntry
    }
  }
}

function annotateFile (inputPath, outputPath, relPath) {
  return new Promise((resolve, reject) => {
    const reader = fs.createReadStream(inputPath).setEncoding('utf8')
    const writer = fs.createWriteStream(outputPath)
    const parser = sax.parser(true)

    parser.onopentag = function (node) {
      const line = parser.line + 1
      const col = parser.column - (parser.position - parser.startTagPosition)
      node.attributes['data-sm'] = `./${relPath}:${line}:${col}`
      const attr = Object.entries(node.attributes)
        .map(([k, v]) => `${k}="${escapeXml(v)}"`)
        .join(' ')
      if (node.isSelfClosing) {
        writer.write(`<${node.name} ${attr}/>`)
      } else {
        writer.write(`<${node.name} ${attr}>`)
      }
    }

    parser.onclosetag = function (tag) {
      if (!parser.tag.isSelfClosing) { 
        writer.write(`</${tag}>`)
      }
    }
  
    parser.ontext = text => writer.write(escapeXml(text))
    parser.oncomment = comment => writer.write(`<!--${comment}-->`)
    parser.onopencdata = () => writer.write('<![CDATA[')
    parser.oncdata = cdata => writer.write(escapeXml(cdata))
    parser.onclosecdata = () => writer.write(']]>')
    parser.onerror = err => reject(err)

    reader.on('data', chunk => parser.write(chunk))
    reader.on('error', err => reject(err))
    reader.on('end', () => writer.end())

    writer.on('finish', () => resolve())
  })
}

async function main (rootDir, pattern) {
  for (const pathEntry of walk(rootDir)) {
    if (pathEntry.dirent.isFile() && pathEntry.dirent.name.match(pattern)) {
      const filePath = pathEntry.path
      const tmpPath = filePath + '.tmp'
      await annotateFile(filePath, tmpPath, path.relative(rootDir, filePath))
      fs.renameSync(tmpPath, filePath)
    }
  }
}

// Given a directory and a filename regex, annotate matched files
main(process.argv[2], new RegExp(process.argv[3], "i"))
  .catch(err => {
    throw new Error(err)
  })
