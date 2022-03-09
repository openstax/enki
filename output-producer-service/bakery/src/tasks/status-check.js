const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { resource, apiRoot, processingStates, completedStates, abortedStates } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/status_check.sh'), { encoding: 'utf-8' })

  const toBashCaseMatch = (list) => {
    return `@(${list.join('|')})`
  }

  return {
    task: 'status check',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [{ name: resource }],
      params: {
        RESOURCE: resource,
        API_ROOT: apiRoot,
        PROCESSING_STATES: toBashCaseMatch(processingStates),
        COMPLETED_STATES: toBashCaseMatch(completedStates),
        ABORTED_STATES: toBashCaseMatch(abortedStates)
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
