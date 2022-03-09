const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { githubSecretCreds } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const bookInput = 'book'
  const contentOutput = 'fetched-book-group'
  const resourceOutput = 'resources'
  const unusedResourceOutput = 'unused-resources'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/fetch_book_group.sh'), { encoding: 'utf-8' })
  return {
    task: 'fetch book group',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [{ name: bookInput }],
      outputs: [
        { name: contentOutput },
        { name: resourceOutput },
        { name: unusedResourceOutput },
        { name: commonLogOutput }
      ],
      params: {
        COLUMNS: 80,
        BOOK_INPUT: bookInput,
        GH_SECRET_CREDS: githubSecretCreds,
        CONTENT_OUTPUT: contentOutput,
        UNUSED_RESOURCE_OUTPUT: unusedResourceOutput,
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
