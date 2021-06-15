import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { ARCHIVE_WEB_STEPS, buildLookUpBook, buildUploadStep, GIT_OR_ARCHIVE } from './step-definitions'
import { KeyValue, DockerDetails, JobType, toConcourseTask, loadEnv, wrapGenericCorgiJob, reportToOutputProducer, Status, RESOURCES, IO as IO, readScript, PDF_OR_WEB, expectEnv, randId, RANDOM_DEV_CODEVERSION_PREFIX, gitTaskMaker, archiveTaskMaker, Env, toDockerSourceSection } from './util'

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

    const taskLookUpBook = (inputSource: RESOURCES, contentSource: GIT_OR_ARCHIVE) => toConcourseTask(env, 'look-up-book', [inputSource], [IO.BOOK, IO.COMMON_LOG], { CONTENT_SOURCE: contentSource, INPUT_SOURCE_DIR: inputSource }, readScript('script/look_up_book.sh'))
    const taskOverrideCommonLog = (message: string) => toConcourseTask(env, 'override-common-log', [], [IO.COMMON_LOG], { MESSAGE: message }, readScript('script/override_common_log.sh'))
    const taskGenPreviewUrls = (contentSource: GIT_OR_ARCHIVE) => toConcourseTask(env, 'generate-preview-urls', [IO.COMMON_LOG, IO.BOOK, IO.ARTIFACTS], [IO.PREVIEW_URLS], { CONTENT_SOURCE: contentSource, CORGI_CLOUDFRONT_URL: true, REX_PREVIEW_URL: 'https://rex-web.herokuapp.com', REX_PROD_PREVIEW_URL: 'https://rex-web-production.herokuapp.com', PREVIEW_APP_URL_PREFIX: 'apps/archive-preview', CODE_VERSION: true }, readScript('script/generate_preview_urls.sh'))

    const buildArchiveOrGitPdfJob = (resource: RESOURCES, gitOrArchive: GIT_OR_ARCHIVE, tasks: any[]) => {
        const report = reportToOutputProducer(resource)
        const lookupBookDef = buildLookUpBook(gitOrArchive, resource)
        const lookupBookTask = gitOrArchive === GIT_OR_ARCHIVE.ARCHIVE ? archiveTaskMaker(env, PDF_OR_WEB.PDF, lookupBookDef.name, lookupBookDef.inputs, lookupBookDef.outputs, lookupBookDef.env) : gitTaskMaker(env, PDF_OR_WEB.PDF, lookupBookDef.name, lookupBookDef.inputs, lookupBookDef.outputs, lookupBookDef.env)
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
        const lookupBookTask = gitOrArchive === GIT_OR_ARCHIVE.ARCHIVE ? archiveTaskMaker(env, PDF_OR_WEB.PDF, lookupBookDef.name, lookupBookDef.inputs, lookupBookDef.outputs, lookupBookDef.env) : gitTaskMaker(env, PDF_OR_WEB.PDF, lookupBookDef.name, lookupBookDef.inputs, lookupBookDef.outputs, lookupBookDef.env)

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

    const gitPdfJob = buildArchiveOrGitPdfJob(RESOURCES.OUTPUT_PRODUCER_GIT_PDF, GIT_OR_ARCHIVE.GIT, [
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-fetch', [IO.BOOK], [IO.FETCHED], {GH_SECRET_CREDS: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-fetch-metadata', [IO.BOOK, IO.FETCHED], [IO.FETCHED, IO.RESOURCES, IO.UNUSED_RESOURCES], {}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-assemble', [IO.BOOK, IO.FETCHED], [IO.ASSEMBLED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-assemble-meta', [IO.BOOK, IO.FETCHED, IO.ASSEMBLED], [IO.ASSEMBLE_META], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-bake', [IO.BOOK, IO.ASSEMBLED], [IO.BAKED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-bake-meta', [IO.BOOK, IO.ASSEMBLE_META, IO.BAKED], [IO.BAKE_META], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-link', [IO.BOOK, IO.BAKED, IO.BAKE_META], [IO.LINKED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-mathify', [IO.BOOK, IO.LINKED, IO.BAKED], [IO.MATHIFIED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-pdfify', [IO.BOOK, IO.MATHIFIED], [IO.ARTIFACTS], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.PDF, 'git-pdfify-meta', [IO.BOOK, IO.ARTIFACTS], [IO.ARTIFACTS], {CORGI_ARTIFACTS_S3_BUCKET: true}),
    ])
    const gitWeb = buildArchiveOrGitWebJob(RESOURCES.OUTPUT_PRODUCER_GIT_WEB, GIT_OR_ARCHIVE.GIT, [
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-fetch', [IO.BOOK], [IO.FETCHED], {GH_SECRET_CREDS: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-fetch-metadata', [IO.BOOK, IO.FETCHED], [IO.FETCHED, IO.RESOURCES, IO.UNUSED_RESOURCES], {}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-assemble', [IO.BOOK, IO.FETCHED], [IO.ASSEMBLED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-assemble-meta', [IO.BOOK, IO.FETCHED, IO.ASSEMBLED], [IO.ASSEMBLE_META], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-bake', [IO.BOOK, IO.ASSEMBLED], [IO.BAKED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-bake-meta', [IO.BOOK, IO.ASSEMBLE_META, IO.BAKED], [IO.BAKE_META], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-link', [IO.BOOK, IO.BAKED, IO.BAKE_META], [IO.LINKED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-disassemble', [IO.BOOK, IO.LINKED, IO.BAKE_META], [IO.DISASSEMBLED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-patch-disassembled-links', [IO.BOOK, IO.DISASSEMBLED], [IO.DISASSEMBLE_LINKED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-jsonify', [IO.BOOK, IO.DISASSEMBLE_LINKED], [IO.JSONIFIED], {ARG_OPT_ONLY_ONE_BOOK: false}),
        gitTaskMaker(env, PDF_OR_WEB.WEB, 'git-upload-book', [IO.BOOK, IO.JSONIFIED, IO.RESOURCES], [IO.ARTIFACTS], {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}),
    ])
    const archivePdfJob = buildArchiveOrGitPdfJob(RESOURCES.OUTPUT_PRODUCER_ARCHIVE_PDF, GIT_OR_ARCHIVE.ARCHIVE, [
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-fetch', [IO.BOOK], [IO.ARCHIVE_FETCHED], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-assemble', [IO.BOOK, IO.ARCHIVE_FETCHED], [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-link-extras', [IO.BOOK, IO.ARCHIVE_BOOK], [IO.ARCHIVE_BOOK], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-bake', [IO.BOOK, IO.ARCHIVE_BOOK], [IO.ARCHIVE_BOOK], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-mathify', [IO.BOOK, IO.ARCHIVE_BOOK], [IO.ARCHIVE_BOOK], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-pdf', [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], [IO.ARTIFACTS], {}),
        archiveTaskMaker(env, PDF_OR_WEB.PDF, 'archive-pdf-metadata', [IO.BOOK, IO.ARTIFACTS], [IO.ARTIFACTS], {CORGI_ARTIFACTS_S3_BUCKET: true}),
    ])
    // See ARCHIVE_WEB_STEPS for all the steps.
    const archiveStepsWithUpload = [...ARCHIVE_WEB_STEPS, buildUploadStep(true, false)]
    const archiveWeb = buildArchiveOrGitWebJob(RESOURCES.OUTPUT_PRODUCER_ARCHIVE_WEB, GIT_OR_ARCHIVE.ARCHIVE, archiveStepsWithUpload.map(({name, inputs, outputs, env: envKeys}) => archiveTaskMaker(env, PDF_OR_WEB.WEB, name, inputs, outputs, envKeys)))

    const resourceTypes = [
        {
            name: 'output-producer',
            type: 'docker-image',
            source: toDockerSourceSection(env)
        }
    ]

    return { jobs: [gitPdfJob, gitWeb, archivePdfJob, archiveWeb], resources, resource_types: resourceTypes }
}

function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    fs.writeFileSync(saveYamlFile, yaml.dump(makePipeline(loadEnv(loadEnvFile))))
}

loadSaveAndDump('./env/corgi-staging.json', './corgi-staging.yml')
loadSaveAndDump('./env/corgi-production.json', './corgi-production.yml')

process.env['CODE_VERSION'] = `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
loadSaveAndDump('./env/corgi-local.json', './corgi-local.yml')
