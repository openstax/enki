const pipeline = (env) => {
  const taskCheckFeed = require('../tasks/check-feed')
  const taskDequeueBook = require('../tasks/dequeue-book')
  const taskFetchBookGroup = require('../tasks/fetch-book-group')
  const taskAssembleBookGroup = require('../tasks/assemble-book-group')
  const taskLinkSingle = require('../tasks/link-single')
  const taskAssembleBookMetaGroup = require('../tasks/assemble-book-metadata-group')
  const taskBakeBookGroup = require('../tasks/bake-book-group')
  const taskBakeBookMetaGroup = require('../tasks/bake-book-metadata-group')
  const taskDisassembleSingle = require('../tasks/disassemble-single')
  const taskPatchDisassembledLinksSingle = require('../tasks/patch-disassembled-links-single')
  const taskJsonifySingle = require('../tasks/jsonify-single')
  const taskValidateXhtml = require('../tasks/validate-xhtml')
  const taskValidateCnxml = require('../tasks/validate-cnxml')
  const taskUploadSingle = require('../tasks/upload-single')
  const taskReportStateComplete = require('../tasks/report-state-complete')

  const awsAccessKeyId = env.S3_ACCESS_KEY_ID
  const awsSecretAccessKey = env.S3_SECRET_ACCESS_KEY
  const codeVersionFromTag = env.IMAGE_TAG || 'version-unknown'
  const githubSecretCreds = env.GH_SECRET_CREDS
  const queueFilename = `${codeVersionFromTag}.${env.WEB_GIT_QUEUE_FILENAME}`
  const queueStatePrefix = 'git-dist'
  const lockedTag = env.IMAGE_TAG || 'trunk'

  const imageOverrides = {
    tag: lockedTag,
    ...env.dockerCredentials
  }

  const resources = [
    {
      name: 'cnx-recipes-output',
      type: 'docker-image',
      source: {
        repository: 'openstax/cnx-recipes-output',
        ...imageOverrides
      }
    },
    {
      name: 's3-queue',
      type: 's3',
      source: {
        bucket: env.WEB_QUEUE_STATE_S3_BUCKET,
        versioned_file: queueFilename,
        initial_version: 'initializing',
        access_key_id: awsAccessKeyId,
        secret_access_key: awsSecretAccessKey
      }
    },
    {
      name: 'ticker',
      type: 'time',
      source: {
        interval: env.PIPELINE_TICK_INTERVAL
      }
    }
  ]

  const feederJob = {
    name: 'feeder',
    plan: [
      { get: 'ticker', trigger: true },
      taskCheckFeed({
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        feedFileUrl: env.WEB_FEED_FILE_URL,
        feedFileFilter: 'git',
        queueStateBucket: env.WEB_QUEUE_STATE_S3_BUCKET,
        queueFilename: queueFilename,
        codeVersion: codeVersionFromTag,
        maxBooksPerRun: env.MAX_BOOKS_PER_TICK,
        statePrefix: queueStatePrefix,
        image: imageOverrides
      })
    ]
  }

  const gitWebHostJob = {
    name: 'git-webhosting-job',
    max_in_flight: 5,
    plan: [
      { get: 's3-queue', trigger: true, version: 'every' },
      { get: 'cnx-recipes-output' },
      taskDequeueBook({
        queueFilename: queueFilename,
        image: imageOverrides,
        contentSource: 'git'
      }),
      taskFetchBookGroup({
        githubSecretCreds: githubSecretCreds,
        image: imageOverrides
      }),
      taskValidateCnxml({
        image: imageOverrides,
        inputSource: 'fetched-book-group',
        modulesPath: 'raw/modules/**/*.cnxml',
        collectionsPath: 'raw/collections/*.xml',
        contentSource: 'git'
      }),
      taskAssembleBookGroup({ image: imageOverrides }),
      taskAssembleBookMetaGroup({ image: imageOverrides }),
      taskBakeBookGroup({ image: imageOverrides }),
      taskBakeBookMetaGroup({ image: imageOverrides }),
      taskLinkSingle({ image: imageOverrides }),
      taskDisassembleSingle({ image: imageOverrides }),
      taskPatchDisassembledLinksSingle({ image: imageOverrides }),
      taskJsonifySingle({
        image: imageOverrides
      }),
      taskValidateXhtml({
        image: imageOverrides,
        inputSource: 'jsonified-single',
        inputPath: '*@*.xhtml',
        validationNames: ['duplicate-id', 'broken-link'],
        contentSource: 'git'
      }),
      taskUploadSingle({
        distBucket: env.WEB_S3_BUCKET,
        distBucketPath: 'apps/archive/',
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        codeVersion: codeVersionFromTag,
        image: imageOverrides
      }),
      taskReportStateComplete({
        image: imageOverrides,
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        queueStateBucket: env.WEB_QUEUE_STATE_S3_BUCKET,
        codeVersion: codeVersionFromTag,
        statePrefix: queueStatePrefix,
        contentSource: 'git'
      })
    ]
  }

  return {
    config: {
      resources: resources,
      jobs: [feederJob, gitWebHostJob]
    }
  }
}

module.exports = pipeline
