import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { ARCHIVE_PDF_STEPS, ARCHIVE_WEB_STEPS_WITH_UPLOAD, buildLookUpBook, GIT_OR_ARCHIVE, GIT_PDF_STEPS, GIT_WEB_STEPS } from './step-definitions'
import { KeyValue, JobType, toConcourseTask, loadEnv, wrapGenericCorgiJob, reportToOutputProducer, Status, RESOURCES, IO, readScript, PDF_OR_WEB, randId, RANDOM_DEV_CODEVERSION_PREFIX, taskMaker, toDockerSourceSection, stepsToTasks } from './util'

const commonLogFile = `${IO.COMMON_LOG}/log`
const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
const genericAbortMessage = 'Job was aborted.'
const s3UploadFailMessage = 'Error occurred upload to S3.'

function makePipeline(env: KeyValue) {
    env.CODE_VERSION = process.env.CODE_VERSION
    const resources = [
        {
            name: RESOURCES.OUTPUT_PRODUCER_ARCHIVE_PDF,
            type: 'output-producer',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.PDF,
                status_id: 1
            }
        },
        {
            name: RESOURCES.OUTPUT_PRODUCER_ARCHIVE_WEB,
            type: 'output-producer',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.DIST_PREVIEW,
                status_id: 1
            }
        },
        {
            name: RESOURCES.OUTPUT_PRODUCER_GIT_PDF,
            type: 'output-producer',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_PDF,
                status_id: 1
            }
        },
        {
            name: RESOURCES.OUTPUT_PRODUCER_GIT_WEB,
            type: 'output-producer',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_DIST_PREVIEW,
                status_id: 1
            }
        },
        {
            name: 's3-pdf',
            type: 's3',
            source: {
                bucket: env.CORGI_ARTIFACTS_S3_BUCKET,
                access_key_id: env.AWS_ACCESS_KEY_ID,
                secret_access_key: env.AWS_SECRET_ACCESS_KEY,
                session_token: env.AWS_SESSION_TOKEN,
                skip_download: true
            }
        }
    ]

    const taskOverrideCommonLog = (message: string) => toConcourseTask(env, 'override-common-log', [], [IO.COMMON_LOG], { MESSAGE: message }, readScript('script/override_common_log.sh'))
    const taskGenPreviewUrls = (contentSource: GIT_OR_ARCHIVE) => toConcourseTask(env, 'generate-preview-urls', [IO.COMMON_LOG, IO.BOOK, IO.ARTIFACTS], [IO.PREVIEW_URLS], { CONTENT_SOURCE: contentSource, CORGI_CLOUDFRONT_URL: true, REX_PREVIEW_URL: 'https://rex-web.herokuapp.com', REX_PROD_PREVIEW_URL: 'https://rex-web-production.herokuapp.com', PREVIEW_APP_URL_PREFIX: 'apps/archive-preview', CODE_VERSION: true }, readScript('script/generate_preview_urls.sh'))

    const buildArchiveOrGitPdfJob = (resource: RESOURCES, gitOrArchive: GIT_OR_ARCHIVE, tasks: any[]) => {
        const report = reportToOutputProducer(resource)
        const lookupBookDef = buildLookUpBook(gitOrArchive, resource)
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, `PDF (${gitOrArchive})`, resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks,
                taskOverrideCommonLog(s3UploadFailMessage),
                {
                    put: 's3-pdf',
                    params: {
                        file: `${IO.ARTIFACTS}/*.pdf`,
                        acl: 'public-read',
                        content_type: 'application/pdf'
                    }
                }
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.ARTIFACTS}/pdf_url`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        })
    }

    const buildArchiveOrGitWebJob = (resource: RESOURCES, gitOrArchive: GIT_OR_ARCHIVE, tasks: any[]) => {
        const report = reportToOutputProducer(resource)
        const lookupBookDef = buildLookUpBook(gitOrArchive, resource)
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, `Web Preview (${gitOrArchive})`, resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks,
                taskGenPreviewUrls(gitOrArchive)
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.PREVIEW_URLS}/content_urls`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        })

    }

    const gitPdfJob = buildArchiveOrGitPdfJob(RESOURCES.OUTPUT_PRODUCER_GIT_PDF, GIT_OR_ARCHIVE.GIT, stepsToTasks(env, PDF_OR_WEB.PDF, GIT_PDF_STEPS))
    const gitWeb = buildArchiveOrGitWebJob(RESOURCES.OUTPUT_PRODUCER_GIT_WEB, GIT_OR_ARCHIVE.GIT, stepsToTasks(env, PDF_OR_WEB.WEB, GIT_WEB_STEPS))
    const archivePdfJob = buildArchiveOrGitPdfJob(RESOURCES.OUTPUT_PRODUCER_ARCHIVE_PDF, GIT_OR_ARCHIVE.ARCHIVE, stepsToTasks(env, PDF_OR_WEB.PDF, ARCHIVE_PDF_STEPS))
    const archiveWebJob = buildArchiveOrGitWebJob(RESOURCES.OUTPUT_PRODUCER_ARCHIVE_WEB, GIT_OR_ARCHIVE.ARCHIVE, stepsToTasks(env, PDF_OR_WEB.WEB, ARCHIVE_WEB_STEPS_WITH_UPLOAD))

    const resourceTypes = [
        {
            name: 'output-producer',
            type: 'docker-image',
            source: toDockerSourceSection(env)
        }
    ]

    return { jobs: [gitPdfJob, gitWeb, archivePdfJob, archiveWebJob], resources, resource_types: resourceTypes }
}

function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    console.log(`Writing pipeline YAML file to ${saveYamlFile}`)
    fs.writeFileSync(saveYamlFile, yaml.dump(makePipeline(loadEnv(loadEnvFile))))
}

loadSaveAndDump('./env/corgi-staging.json', './corgi-staging.yml')
loadSaveAndDump('./env/corgi-production.json', './corgi-production.yml')

process.env['CODE_VERSION'] = `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
loadSaveAndDump('./env/corgi-local.json', './corgi-local.yml')
