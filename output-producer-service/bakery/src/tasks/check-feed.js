const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { awsAccessKeyId, awsSecretAccessKey, feedFileUrl, feedFileFilter, codeVersion, queueStateBucket, queueFilename, maxBooksPerRun, statePrefix } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  return {
    task: 'check feed',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      params: {
        AWS_ACCESS_KEY_ID: `${awsAccessKeyId}`,
        AWS_SECRET_ACCESS_KEY: `${awsSecretAccessKey}`
      },
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          curl ${feedFileUrl} -o book-feed.json
          check-feed book-feed.json "${codeVersion}" "${queueStateBucket}" "${queueFilename}" "${maxBooksPerRun}" "${statePrefix}" "${feedFileFilter}"
        `
        ]
      }
    }
  }
}

module.exports = task
