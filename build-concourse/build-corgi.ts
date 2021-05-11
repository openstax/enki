import * as dedent from 'dedent'
import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { DockerDetails, JobType, toConcourseTask, TaskNode, wrapGenericCorgiJob, reportToOutputProducer, Status, docker, RESOURCES, IN_OUT, readScript, populateEnv, devOrProductionSettings, variantMaker, PDF_OR_WEB } from './util'

const commonLogFile = `${IN_OUT.COMMON_LOG}/log`
const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
const genericAbortMessage = 'Job was aborted.'
const s3UploadFailMessage = 'Error occurred upload to S3.'

const myEnv = populateEnv({AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false})
const resources = [
    // {
    //   name: 'output-producer-pdf',
    //   type: 'output-producer',
    //   source: {
    //     api_root: docker.corgiApiUrl,
    //     job_type_id: JobType.PDF,
    //     status_id: 1
    //   }
    // },
    // {
    //   name: 'output-producer-dist-preview',
    //   type: 'output-producer',
    //   source: {
    //     api_root: docker.corgiApiUrl,
    //     job_type_id: JobType.DIST_PREVIEW,
    //     status_id: 1
    //   }
    // },
    {
      name: RESOURCES.OUTPUT_PRODUCER_GIT_PDF,
      type: 'output-producer',
      source: {
        api_root: docker.corgiApiUrl,
        job_type_id: JobType.GIT_PDF,
        status_id: 1
      }
    },
    // {
    //   name: 'output-producer-git-dist-preview',
    //   type: 'output-producer',
    //   source: {
    //     api_root: docker.corgiApiUrl,
    //     job_type_id: JobType.GIT_DIST_PREVIEW,
    //     status_id: 1
    //   }
    // },
    {
      name: 's3-pdf',
      type: 's3',
      source: {
        bucket: devOrProductionSettings().artifactBucket,
        access_key_id: myEnv.AWS_ACCESS_KEY_ID,
        secret_access_key: myEnv.AWS_SECRET_ACCESS_KEY,
        skip_download: true
      }
    }
  ]

enum GIT_OR_ARCHIVE {
    GIT = 'git',
    ARCHIVE = 'archive'
}
const taskLookUpBook = (inputSource: RESOURCES, contentSource: GIT_OR_ARCHIVE) => toConcourseTask('look-up-book', [inputSource], [IN_OUT.BOOK, IN_OUT.COMMON_LOG], {CONTENT_SOURCE: contentSource}, dedent`
    exec > >(tee ${IN_OUT.COMMON_LOG}/log >&2) 2>&1

    tail ${inputSource}/*
    cp ${inputSource}/id ${IN_OUT.BOOK}/job_id
    cp ${inputSource}/version ${IN_OUT.BOOK}/version
    cp ${inputSource}/collection_style ${IN_OUT.BOOK}/style
    case $CONTENT_SOURCE in
        archive)
            cp ${inputSource}/collection_id ${IN_OUT.BOOK}/collection_id
            cp ${inputSource}/content_server ${IN_OUT.BOOK}/server
            wget -q -O jq 'https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64' && chmod +x jq
            server_shortname="$(cat ${inputSource}/job.json | ./jq -r '.content_server.name')"
            echo "$server_shortname" >${IN_OUT.BOOK}/server_shortname
            pdf_filename="$(cat ${IN_OUT.BOOK}/collection_id)-$(cat ${IN_OUT.BOOK}/version)-$(cat ${IN_OUT.BOOK}/server_shortname)-$(cat ${IN_OUT.BOOK}/job_id).pdf"
            echo "$pdf_filename" > ${IN_OUT.BOOK}/pdf_filename
            ;;
        git)
            cat ${inputSource}/collection_id | awk -F'/' '{ print $1 }' > ${IN_OUT.BOOK}/repo
            cat ${inputSource}/collection_id | awk -F'/' '{ print $2 }' | sed 's/ *$//' > ${IN_OUT.BOOK}/slug
            pdf_filename="$(cat ${IN_OUT.BOOK}/slug)-$(cat ${IN_OUT.BOOK}/version)-git-$(cat ${IN_OUT.BOOK}/job_id).pdf"
            echo "$pdf_filename" > ${IN_OUT.BOOK}/pdf_filename

            echo 'Using test repository'
            echo 'philschatz/tiny-book' > ${IN_OUT.BOOK}/repo
            echo 'book-slug1' > ${IN_OUT.BOOK}/slug
            ;;
        *)
            echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
            exit 1
            ;;
    esac
    `)



const taskOverrideCommonLog = (message: string) => toConcourseTask('generate-preview-urls', [], [IN_OUT.COMMON_LOG], {MESSAGE: message, COMMON_LOG_DIR: IN_OUT.COMMON_LOG}, readScript('script/override_common_log.sh'))

let report
report = reportToOutputProducer(RESOURCES.OUTPUT_PRODUCER_GIT_PDF)
  const gitPdfJob = wrapGenericCorgiJob('PDF (git)', RESOURCES.OUTPUT_PRODUCER_GIT_PDF, {
    do: [
      report(Status.ASSIGNED, {
        worker_version: docker.tag
      }),
      taskLookUpBook(RESOURCES.OUTPUT_PRODUCER_GIT_PDF, GIT_OR_ARCHIVE.GIT),
      report(Status.PROCESSING),
      variantMaker(PDF_OR_WEB.PDF),
      taskOverrideCommonLog(s3UploadFailMessage),
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


const resourceTypes = [
    {
      name: 'output-producer',
      type: 'docker-image',
      source: {
        repository: 'openstax/output-producer-resource',
        tag: "20210427.153250"
        // repository: docker.repository,
        // tag: docker.tag
      }
    }
  ]

  console.warn('Hardcoded output-producer-resource to a specific version. This resource type should be absorbed into the pipeline repo')
fs.writeFileSync('./build-corgi.yml', yaml.dump({ jobs: [gitPdfJob], resources, resource_types: resourceTypes }))