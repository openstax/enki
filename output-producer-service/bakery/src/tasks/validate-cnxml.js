const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { inputSource, modulesPath, collectionsPath, contentSource: maybeContentSource } = taskArgs
  const imageDefault = {
    name: 'openstax/nebuchadnezzar',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  const bookInput = 'book'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/validate_cnxml.sh'), { encoding: 'utf-8' })

  return {
    task: 'validate cnxml',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: `${inputSource}` }
      ],
      outputs: [
        { name: commonLogOutput }
      ],
      params: {
        CONTENT_SOURCE: contentSource,
        BOOK_INPUT: bookInput,
        COMMON_LOG_DIR: commonLogOutput,
        INPUT_SOURCE: `${inputSource}`,
        COLLECTIONS_PATH: `${collectionsPath}`,
        MODULES_PATH: `${modulesPath}`
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
