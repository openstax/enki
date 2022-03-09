const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { message } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const commonLogOutput = 'common-log'

  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/override_common_log.sh'), { encoding: 'utf-8' })

  return {
    task: 'override common log',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      outputs: [
        { name: commonLogOutput }
      ],
      params: {
        MESSAGE: message,
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
