const { constructImageSource } = require('../task-util/task-util')
const fs = require('fs')
const path = require('path')

const task = (taskArgs) => {
  const { awsAccessKeyId, awsSecretAccessKey, distBucket, codeVersion, distBucketPath } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  if (!distBucketPath.endsWith('/') || distBucketPath.length === 0) {
    throw Error('distBucketPath must represent some directory-like path in s3')
  }
  const distBucketPrefix = `${distBucketPath}${codeVersion}`
  const bookInput = 'book'
  const jsonifiedInput = 'jsonified-single'
  const resourceInput = 'resources'
  const uploadOutput = 'upload-single'
  const commonLogOutput = 'common-log'
  const shellScript = fs.readFileSync(path.resolve(__dirname, '../scripts/upload_single.sh'), { encoding: 'utf-8' })

  return {
    task: 'upload single',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: bookInput },
        { name: jsonifiedInput },
        { name: resourceInput }
      ],
      outputs: [
        { name: uploadOutput },
        { name: commonLogOutput }
      ],
      params: {
        AWS_ACCESS_KEY_ID: `${awsAccessKeyId}`,
        AWS_SECRET_ACCESS_KEY: `${awsSecretAccessKey}`,
        BUCKET: distBucket,
        BUCKET_PREFIX: distBucketPrefix,
        BOOK_INPUT: bookInput,
        JSONIFIED_INPUT: jsonifiedInput,
        RESOURCE_INPUT: resourceInput,
        UPLOAD_OUTPUT: uploadOutput,
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
