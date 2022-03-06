const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { awsAccessKeyId, awsSecretAccessKey, queueStateBucket, codeVersion, statePrefix, contentSource: maybeContentSource } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  return {
    task: 'report book complete',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      params: {
        AWS_ACCESS_KEY_ID: `${awsAccessKeyId}`,
        AWS_SECRET_ACCESS_KEY: `${awsSecretAccessKey}`,
        CONTENT_SOURCE: contentSource
      },
      inputs: [
        { name: 'book' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`

          case $CONTENT_SOURCE in
          archive)
            book_id="$(cat book/collection_id)"
            ;;
          git)
            book_id="$(cat book/slug)"
            ;;
          *)
            echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
            exit 1
            ;;
          esac

          version="$(cat book/version)"
          complete_filename=".${statePrefix}.$book_id@$version.complete"
          date -Iseconds > "/tmp/$complete_filename"
          aws s3 cp "/tmp/$complete_filename" "s3://${queueStateBucket}/${codeVersion}/$complete_filename"
        `
        ]
      }
    }
  }
}

module.exports = task
