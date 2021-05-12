import * as dedent from 'dedent'
import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { DockerDetails, JobType, toConcourseTask, TaskNode, wrapGenericCorgiJob, reportToOutputProducer, Status, docker, RESOURCES, IO as IO, readScript, populateEnv, devOrProductionSettings, variantMaker, PDF_OR_WEB } from './util'

const commonLogFile = `${IO.COMMON_LOG}/log`
const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
const genericAbortMessage = 'Job was aborted.'
const s3UploadFailMessage = 'Error occurred upload to S3.'

const myEnv = populateEnv({ AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false })
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
            bucket: devOrProductionSettings().artifactsBucket,
            access_key_id: myEnv.AWS_ACCESS_KEY_ID,
            secret_access_key: myEnv.AWS_SECRET_ACCESS_KEY,
            session_token: myEnv.AWS_SESSION_TOKEN,
            skip_download: true
        }
    }
]

enum GIT_OR_ARCHIVE {
    GIT = 'git',
    ARCHIVE = 'archive'
}
const taskLookUpBook = (inputSource: RESOURCES, contentSource: GIT_OR_ARCHIVE) => toConcourseTask('look-up-book', [inputSource], [IO.BOOK, IO.COMMON_LOG], { CONTENT_SOURCE: contentSource, INPUT_SOURCE_DIR: inputSource }, readScript('script/look_up_book.sh'))



const taskOverrideCommonLog = (message: string) => toConcourseTask('override-common-log', [], [IO.COMMON_LOG], { MESSAGE: message }, readScript('script/override_common_log.sh'))
const taskGeneratePreviewUrls = (message: string) => toConcourseTask('generate-preview-urls', [], [IO.COMMON_LOG], { MESSAGE: message }, readScript('script/generate_preview_urls.sh'))

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
                file: `${IO.ARTIFACTS_SINGLE}/*.pdf`,
                acl: 'public-read',
                content_type: 'application/pdf'
            }
        }
    ],
    on_success: report(Status.SUCCEEDED, {
        pdf_url: `${IO.ARTIFACTS_SINGLE}/pdf_url`
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