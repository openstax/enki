const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { bucketName } = taskArgs
  const imageDefault = {
    name: 'openstax/princexml',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const bookInput = 'book'
  const fetchedInput = 'fetched-book-group'
  const fetchedResourcesInput = 'resources'
  const styleInput = 'group-style'
  const rexLinkedInput = 'rex-linked'
  const artifactsOutput = 'artifacts-single'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/pdfify_single.sh'), { encoding: 'utf-8' })

  return {
    task: 'build pdf single',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: fetchedInput },
        { name: fetchedResourcesInput },
        { name: styleInput },
        { name: rexLinkedInput }
      ],
      outputs: [
        { name: artifactsOutput },
        { name: commonLogOutput }
      ],
      params: {
        ARTIFACTS_OUTPUT: artifactsOutput,
        REXLINKED_INPUT: rexLinkedInput,
        STYLE_INPUT: styleInput,
        BUCKET_NAME: bucketName,
        BOOK_INPUT: bookInput,
        COMMON_LOG_DIR: commonLogOutput
      },
      run: {
        user: 'root',
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
