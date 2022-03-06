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
  const disassembledInput = 'disassembled-linked-single'
  const jsonifiedOutput = 'jsonified-single'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/jsonify_single.sh'), { encoding: 'utf-8' })

  return {
    task: 'jsonify single',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: disassembledInput }
      ],
      outputs: [
        { name: jsonifiedOutput },
        { name: commonLogOutput }
      ],
      params: {
        DISASSEMBLED_INPUT: disassembledInput,
        JSONIFIED_OUTPUT: jsonifiedOutput,
        BOOK_INPUT: bookInput,
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
