const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const singleBookFlag = taskArgs != null && taskArgs.singleBookFlag != null ? taskArgs.singleBookFlag : false
  const bookSlug = taskArgs != null && taskArgs.slug != null ? taskArgs.slug : ''
  const targetBook = singleBookFlag ? bookSlug : ''
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const fetchedInput = 'fetched-book-group'
  const assembledInput = 'assembled-book-group'
  const outputName = 'assembled-book-metadata-group'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/assemble_book_metadata_group.sh'), { encoding: 'utf-8' })

  return {
    task: 'assemble book metadata group',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: fetchedInput },
        { name: assembledInput }
      ],
      outputs: [
        { name: outputName },
        { name: commonLogOutput }
      ],
      params: {
        OUTPUT_NAME: outputName,
        ASSEMBLED_INPUT: assembledInput,
        FETCHED_INPUT: fetchedInput,
        TARGET_BOOK: targetBook,
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
