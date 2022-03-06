const pipeline = (env) => {
  const taskCheckFeed = require('../tasks/check-feed')
  const taskDequeueBook = require('../tasks/dequeue-book')
  const taskFetchBook = require('../tasks/fetch-book')
  const taskAssembleBook = require('../tasks/assemble-book')
  const taskLinkExtras = require('../tasks/link-extras')
  const taskAssembleBookMeta = require('../tasks/assemble-book-metadata')
  const taskBakeBook = require('../tasks/bake-book')
  const taskBakeBookMeta = require('../tasks/bake-book-metadata')
  const taskChecksumBook = require('../tasks/checksum-book')
  const taskDisassembleBook = require('../tasks/disassemble-book')
  const taskValidateXhtml = require('../tasks/validate-xhtml')
  const taskValidateCnxml = require('../tasks/validate-cnxml')
  const taskGdocifyBook = require('../tasks/gdocify-book')
  const taskConvertDocx = require('../tasks/convert-docx')
  const taskUploadDocx = require('../tasks/upload-docx')

  const awsAccessKeyId = env.S3_ACCESS_KEY_ID
  const awsSecretAccessKey = env.S3_SECRET_ACCESS_KEY
  const codeVersionFromTag = env.IMAGE_TAG || 'version-unknown'
  const queueFilename = `${codeVersionFromTag}.${env.GDOC_QUEUE_FILENAME}`
  const parentGoogleFolderId = env.GDOC_GOOGLE_FOLDER_ID
  const queueStatePrefix = 'gdoc'

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
        feedFileUrl: env.GDOC_FEED_FILE_URL,
        feedFileFilter: 'archive',
        queueStateBucket: env.WEB_QUEUE_STATE_S3_BUCKET,
        queueFilename: queueFilename,
        codeVersion: codeVersionFromTag,
        maxBooksPerRun: env.MAX_BOOKS_PER_TICK,
        statePrefix: queueStatePrefix,
        image: imageOverrides
      })
    ]
  }

  const bakeryJob = {
    name: 'bakery',
    max_in_flight: 5,
    plan: [
      { get: 's3-queue', trigger: true, version: 'every' },
      { get: 'cnx-recipes-output' },
      taskDequeueBook({
        queueFilename: queueFilename,
        image: imageOverrides
      }),
      taskFetchBook({ image: imageOverrides }),
      taskValidateCnxml({
        image: imageOverrides,
        inputSource: 'fetched-book',
        modulesPath: 'raw/**/index.cnxml',
        collectionsPath: 'raw/collection.xml'
      }),
      taskAssembleBook({ image: imageOverrides }),
      taskLinkExtras({
        image: imageOverrides,
        server: 'archive.cnx.org'
      }),
      taskAssembleBookMeta({ image: imageOverrides }),
      taskBakeBook({ image: imageOverrides }),
      taskBakeBookMeta({ image: imageOverrides }),
      taskChecksumBook({ image: imageOverrides }),
      taskDisassembleBook({ image: imageOverrides }),
      taskValidateXhtml({
        image: imageOverrides,
        inputSource: 'disassembled-book',
        inputPath: 'disassembled/*@*.xhtml',
        validationNames: ['duplicate-id']
      }),
      taskGdocifyBook({ image: imageOverrides }),
      taskConvertDocx({ image: imageOverrides }),
      taskUploadDocx({
        image: imageOverrides,
        parentGoogleFolderId: parentGoogleFolderId,
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        queueStateBucket: env.WEB_QUEUE_STATE_S3_BUCKET,
        codeVersion: codeVersionFromTag,
        statePrefix: queueStatePrefix
      })
    ]
  }

  return {
    config: {
      resources: resources,
      jobs: [feederJob, bakeryJob]
    }
  }
}

module.exports = pipeline
