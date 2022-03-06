const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const bookInput = 'book'
  const resourceLinkedInput = 'linked-single'
  const bakedBookMetaInput = 'baked-book-metadata-group'
  const disassembledOutput = 'disassembled-single'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/disassemble_single.sh'), { encoding: 'utf-8' })

  return {
    task: 'disassemble single',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: resourceLinkedInput },
        { name: bakedBookMetaInput }
      ],
      outputs: [
        { name: disassembledOutput },
        { name: commonLogOutput }
      ],
      params: {
        BOOK_INPUT: bookInput,
        RESOURCE_LINKED_INPUT: resourceLinkedInput,
        BAKED_BOOK_META_INPUT: bakedBookMetaInput,
        DISASSEMBLED_OUTPUT: disassembledOutput,
        COMMON_LOG_DIR: commonLogOutput
      },
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          shellScript
        ]
      }
    }
  }
}

module.exports = task
