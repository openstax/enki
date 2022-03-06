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

  const bookInput = 'book'
  const fetchedInput = 'fetched-book-group'
  const bakedInput = 'baked-book-group'
  const bakedMetaInput = 'baked-book-metadata-group'
  const linkedOutput = 'linked-single'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/link_single.sh'), { encoding: 'utf-8' })

  return {
    task: 'link single',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: fetchedInput },
        { name: bakedInput },
        { name: bakedMetaInput }
      ],
      outputs: [
        { name: linkedOutput },
        { name: commonLogOutput }
      ],
      params: {
        LINKED_OUTPUT: linkedOutput,
        FETCHED_INPUT: fetchedInput,
        BAKED_INPUT: bakedInput,
        BAKED_META_INPUT: bakedMetaInput,
        BOOK_INPUT: bookInput,
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
