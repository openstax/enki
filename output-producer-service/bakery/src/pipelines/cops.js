const pipeline = (env) => {
  const taskLookUpBook = require('../tasks/look-up-book')
  const taskFetchBook = require('../tasks/fetch-book')
  const taskAssembleBook = require('../tasks/assemble-book')
  const taskLinkExtras = require('../tasks/link-extras')
  const taskBakeBook = require('../tasks/bake-book')
  const taskMathifyBook = require('../tasks/mathify-book')
  const taskBuildPdf = require('../tasks/build-pdf')
  const taskValidateXhtml = require('../tasks/validate-xhtml')

  const taskAssembleBookMeta = require('../tasks/assemble-book-metadata')
  const taskBakeBookMeta = require('../tasks/bake-book-metadata')
  const taskChecksumBook = require('../tasks/checksum-book')
  const taskDisassembleBook = require('../tasks/disassemble-book')
  const taskPatchDisassembledLinks = require('../tasks/patch-disassembled-links')
  const taskJsonifyBook = require('../tasks/jsonify-book')
  const taskUploadBook = require('../tasks/upload-book')

  const taskFetchBookGroup = require('../tasks/fetch-book-group')
  const taskAssembleBookGroup = require('../tasks/assemble-book-group')
  const taskAssembleBookMetadataGroup = require('../tasks/assemble-book-metadata-group')
  const taskBakeBookGroup = require('../tasks/bake-book-group')
  const taskBakeBookMetadataGroup = require('../tasks/bake-book-metadata-group')
  const taskLinkSingle = require('../tasks/link-single')
  const taskDisassembleSingle = require('../tasks/disassemble-single')
  const taskPatchDisassembledLinksSingle = require('../tasks/patch-disassembled-links-single')
  const taskJsonifySingle = require('../tasks/jsonify-single')
  const taskUploadSingle = require('../tasks/upload-single')
  const taskMathifySingle = require('../tasks/mathify-single')
  const taskPdfifySingle = require('../tasks/pdfify-single')
  const taskGenPreviewUrls = require('../tasks/gen-preview-urls')
  const taskLinkRex = require('../tasks/link-rex')

  const taskOverrideCommonLog = require('../tasks/override-common-log')
  const taskStatusCheck = require('../tasks/status-check')

  const lockedTag = env.IMAGE_TAG || 'trunk'
  const awsAccessKeyId = env.S3_ACCESS_KEY_ID
  const awsSecretAccessKey = env.S3_SECRET_ACCESS_KEY
  const codeVersionFromTag = env.IMAGE_TAG || 'version-unknown'
  const imageOverrides = {
    tag: lockedTag,
    ...env.dockerCredentials
  }
  const buildLogRetentionDays = 14
  const distBucketPath = 'apps/archive-preview/'

  const commonLogFile = 'common-log/log'
  const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
  const genericAbortMessage = 'Job was aborted.'
  const s3UploadFailMessage = 'Error occurred upload to S3.'

  // FIXME: These mappings should be in the COPS resource
  const JobType = Object.freeze({
    PDF: 1,
    DIST_PREVIEW: 2,
    GIT_PDF: 3,
    GIT_DIST_PREVIEW: 4
  })
  const Status = Object.freeze({
    QUEUED: 1,
    ASSIGNED: 2,
    PROCESSING: 3,
    FAILED: 4,
    SUCCEEDED: 5,
    ABORTED: 6
  })

  const reportToOutputProducer = (resource) => {
    return (status, extras) => {
      return {
        put: resource,
        params: {
          id: `${resource}/id`,
          status_id: status,
          ...extras
        }
      }
    }
  }

  const runWithStatusCheck = (resource, step) => {
    const reporter = reportToOutputProducer(resource)
    return {
      in_parallel: {
        fail_fast: true,
        steps: [
          step,
          {
            do: [
              taskStatusCheck({
                resource: resource,
                apiRoot: env.COPS_TARGET,
                image: imageOverrides,
                processingStates: [Status.QUEUED, Status.ASSIGNED, Status.PROCESSING],
                completedStates: [Status.FAILED, Status.SUCCEEDED],
                abortedStates: [Status.ABORTED]
              })
            ],
            on_failure: reporter(Status.ABORTED, {
              error_message: genericAbortMessage
            })
          }
        ]
      }
    }
  }

  const wrapGenericCorgiJob = (jobName, resource, step) => {
    const report = reportToOutputProducer(resource)
    return {
      name: jobName,
      build_log_retention: {
        days: buildLogRetentionDays
      },
      plan: [
        {
          do: [
            { get: resource, trigger: true, version: 'every' }
          ],
          on_failure: report(Status.FAILED, {
            error_message: genericErrorMessage
          })
        },
        runWithStatusCheck(resource, step)
      ],
      on_error: report(Status.FAILED, {
        error_message: genericErrorMessage
      }),
      on_abort: report(Status.ABORTED, {
        error_message: genericAbortMessage
      })
    }
  }

  const resourceTypes = [
    {
      name: 'output-producer',
      type: 'docker-image',
      source: {
        repository: 'openstax/output-producer-resource',
        ...imageOverrides
      }
    }
  ]

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
      name: 'output-producer-pdf',
      type: 'output-producer',
      source: {
        api_root: env.COPS_TARGET,
        job_type_id: JobType.PDF,
        status_id: 1
      }
    },
    {
      name: 'output-producer-dist-preview',
      type: 'output-producer',
      source: {
        api_root: env.COPS_TARGET,
        job_type_id: JobType.DIST_PREVIEW,
        status_id: 1
      }
    },
    {
      name: 'output-producer-git-pdf',
      type: 'output-producer',
      source: {
        api_root: env.COPS_TARGET,
        job_type_id: JobType.GIT_PDF,
        status_id: 1
      }
    },
    {
      name: 'output-producer-git-dist-preview',
      type: 'output-producer',
      source: {
        api_root: env.COPS_TARGET,
        job_type_id: JobType.GIT_DIST_PREVIEW,
        status_id: 1
      }
    },
    {
      name: 's3-pdf',
      type: 's3',
      source: {
        bucket: env.COPS_ARTIFACTS_S3_BUCKET,
        access_key_id: awsAccessKeyId,
        secret_access_key: awsSecretAccessKey,
        skip_download: true
      }
    }
  ]

  let resource
  let report

  resource = 'output-producer-git-pdf'
  report = reportToOutputProducer(resource)
  const gitPdfJob = wrapGenericCorgiJob('PDF (git)', resource, {
    do: [
      report(Status.ASSIGNED, {
        worker_version: lockedTag
      }),
      { get: 'cnx-recipes-output' },
      taskLookUpBook({ inputSource: resource, image: imageOverrides, contentSource: 'git' }),
      report(Status.PROCESSING),
      taskFetchBookGroup({
        image: imageOverrides,
        githubSecretCreds: env.GH_SECRET_CREDS
      }),
      taskAssembleBookGroup({ image: imageOverrides }),
      taskAssembleBookMetadataGroup({ image: imageOverrides }),
      taskBakeBookGroup({ image: imageOverrides }),
      taskBakeBookMetadataGroup({ image: imageOverrides }),
      taskLinkSingle({ image: imageOverrides }),
      taskMathifySingle({ image: imageOverrides }),
      taskValidateXhtml({
        image: imageOverrides,
        inputSource: 'mathified-single',
        inputPath: '*.mathified.xhtml',
        validationNames: ['link-to-duplicate-id', 'broken-link'],
        contentSource: 'git'
      }),
      taskLinkRex({
        image: imageOverrides,
        inputSource: 'mathified-single',
        contentSource: 'git'
      }),
      taskPdfifySingle({ bucketName: env.COPS_ARTIFACTS_S3_BUCKET, image: imageOverrides }),
      taskOverrideCommonLog({ image: imageOverrides, message: s3UploadFailMessage }),
      {
        put: 's3-pdf',
        params: {
          file: 'artifacts-single/*.pdf',
          acl: 'public-read',
          content_type: 'application/pdf'
        }
      }
    ],
    on_success: report(Status.SUCCEEDED, {
      pdf_url: 'artifacts-single/pdf_url'
    }),
    on_failure: report(Status.FAILED, {
      error_message_file: commonLogFile
    })
  })

  resource = 'output-producer-pdf'
  report = reportToOutputProducer(resource)
  const pdfJob = wrapGenericCorgiJob('PDF', resource, {
    do: [
      report(Status.ASSIGNED, {
        worker_version: lockedTag
      }),
      { get: 'cnx-recipes-output' },
      taskLookUpBook({ inputSource: resource, image: imageOverrides }),
      report(Status.PROCESSING),
      taskFetchBook({ image: imageOverrides }),
      taskAssembleBook({ image: imageOverrides }),
      taskLinkExtras({
        image: imageOverrides,
        server: 'archive.cnx.org'
      }),
      taskBakeBook({ image: imageOverrides }),
      taskMathifyBook({ image: imageOverrides }),
      taskValidateXhtml({
        image: imageOverrides,
        inputSource: 'mathified-book',
        inputPath: 'collection.mathified.xhtml',
        validationNames: ['link-to-duplicate-id', 'broken-link']
      }),
      taskLinkRex({
        image: imageOverrides,
        inputSource: 'mathified-book'
      }),
      taskBuildPdf({ bucketName: env.COPS_ARTIFACTS_S3_BUCKET, image: imageOverrides }),
      taskOverrideCommonLog({ image: imageOverrides, message: s3UploadFailMessage }),
      {
        put: 's3-pdf',
        params: {
          file: 'artifacts/*.pdf',
          acl: 'public-read',
          content_type: 'application/pdf'
        }
      }
    ],
    on_success: report(Status.SUCCEEDED, {
      pdf_url: 'artifacts/pdf_url'
    }),
    on_failure: report(Status.FAILED, {
      error_message_file: commonLogFile
    })
  })

  resource = 'output-producer-dist-preview'
  report = reportToOutputProducer(resource)
  const distPreviewJob = wrapGenericCorgiJob('Web Preview', resource, {
    do: [
      report(Status.ASSIGNED, {
        worker_version: lockedTag
      }),
      { get: 'cnx-recipes-output' },
      taskLookUpBook({ inputSource: resource, image: imageOverrides }),
      report(Status.PROCESSING),
      taskFetchBook({ image: imageOverrides }),
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
      taskPatchDisassembledLinks({ image: imageOverrides }),
      taskJsonifyBook({ image: imageOverrides }),
      taskValidateXhtml({
        image: imageOverrides,
        inputSource: 'jsonified-book',
        inputPath: 'jsonified/*@*.xhtml',
        validationNames: ['duplicate-id', 'broken-link']
      }),
      taskUploadBook({
        image: imageOverrides,
        distBucket: env.COPS_ARTIFACTS_S3_BUCKET,
        distBucketPath: distBucketPath,
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        codeVersion: codeVersionFromTag
      }),
      taskGenPreviewUrls({
        image: imageOverrides,
        distBucketPath: distBucketPath,
        codeVersion: codeVersionFromTag,
        jsonifiedInput: 'jsonified-book',
        cloudfrontUrl: env.COPS_CLOUDFRONT_URL
      })
    ],
    on_success: report(Status.SUCCEEDED, {
      pdf_url: 'preview-urls/content_urls'
    }),
    on_failure: report(Status.FAILED, {
      error_message_file: commonLogFile
    })
  })

  resource = 'output-producer-git-dist-preview'
  report = reportToOutputProducer(resource)
  const gitDistPreviewJob = wrapGenericCorgiJob('Web Preview (git)', resource, {
    do: [
      report(Status.ASSIGNED, {
        worker_version: lockedTag
      }),
      { get: 'cnx-recipes-output' },
      taskLookUpBook({ inputSource: resource, image: imageOverrides, contentSource: 'git' }),
      report(Status.PROCESSING),
      taskFetchBookGroup({
        image: imageOverrides,
        githubSecretCreds: env.GH_SECRET_CREDS
      }),
      taskAssembleBookGroup({ image: imageOverrides }),
      taskAssembleBookMetadataGroup({ image: imageOverrides }),
      taskBakeBookGroup({ image: imageOverrides }),
      taskBakeBookMetadataGroup({ image: imageOverrides }),
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
        image: imageOverrides,
        distBucket: env.COPS_ARTIFACTS_S3_BUCKET,
        distBucketPath: distBucketPath,
        awsAccessKeyId: awsAccessKeyId,
        awsSecretAccessKey: awsSecretAccessKey,
        codeVersion: codeVersionFromTag
      }),
      taskGenPreviewUrls({
        image: imageOverrides,
        distBucketPath: distBucketPath,
        codeVersion: codeVersionFromTag,
        cloudfrontUrl: env.COPS_CLOUDFRONT_URL,
        jsonifiedInput: 'jsonified-single',
        contentSource: 'git'
      })
    ],
    on_success: report(Status.SUCCEEDED, {
      pdf_url: 'preview-urls/content_urls'
    }),
    on_failure: report(Status.FAILED, {
      error_message_file: commonLogFile
    })
  })

  return {
    config: {
      resource_types: resourceTypes,
      resources: resources,
      jobs: [pdfJob, distPreviewJob, gitPdfJob, gitDistPreviewJob]
    }
  }
}

module.exports = pipeline
