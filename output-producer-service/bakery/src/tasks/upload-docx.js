const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { parentGoogleFolderId, awsAccessKeyId, awsSecretAccessKey, queueStateBucket, codeVersion, statePrefix } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  return {
    task: 'upload docx',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      params: {
        GOOGLE_SERVICE_ACCOUNT_CREDENTIALS: '((google-service-account-credentials))',
        AWS_ACCESS_KEY_ID: `${awsAccessKeyId}`,
        AWS_SECRET_ACCESS_KEY: `${awsSecretAccessKey}`
      },
      inputs: [
        { name: 'book' },
        { name: 'docx-book' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-ce',
          dedent`
          echo "$GOOGLE_SERVICE_ACCOUNT_CREDENTIALS" > /tmp/service_account_credentials.json
          # Secret credentials above, do not use set -x above this line.
          set -x
          collection_id="$(cat book/collection_id)"
          book_legacy_version="$(cat book/version)"
          docx_dir="docx-book/$collection_id/docx"
          book_metadata="docx-book/$collection_id/raw/metadata.json"
          book_title="$(cat $book_metadata | jq -r '.title')"
          upload-docx "$docx_dir" "$book_title" "${parentGoogleFolderId}" /tmp/service_account_credentials.json
          complete_filename=".${statePrefix}.$collection_id@$book_legacy_version.complete"
          date -Iseconds > "/tmp/$complete_filename"
          aws s3 cp "/tmp/$complete_filename" "s3://${queueStateBucket}/${codeVersion}/$complete_filename"
        `
        ]
      }
    }
  }
}

module.exports = task
