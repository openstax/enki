const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/nebuchadnezzar',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const singleBookFlag = taskArgs != null && taskArgs.singleBookFlag != null ? taskArgs.singleBookFlag : false
  const bookSlug = taskArgs != null && taskArgs.slug != null ? taskArgs.slug : ''
  const targetBook = singleBookFlag ? bookSlug : ''
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const inputName = 'fetched-book-group'
  const assembledOutput = 'assembled-book-group'
  const commonLogOutput = 'common-log'

  const rawCollectionDir = `${inputName}/raw`
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/assemble_book_group.sh'), { encoding: 'utf-8' })

  return {
    task: 'assemble book group',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: inputName }
      ],
      outputs: [
        { name: assembledOutput },
        { name: commonLogOutput }
      ],
      params: {
        ASSEMBLED_OUTPUT: assembledOutput,
        RAW_COLLECTION_DIR: rawCollectionDir,
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
