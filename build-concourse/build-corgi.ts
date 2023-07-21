import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { buildLookUpBook, GIT_PDF_STEPS, GIT_WEB_STEPS, GIT_GDOC_STEPS, GIT_EPUB_STEPS } from './step-definitions'
import { KeyValue, JobType, toConcourseTask, loadEnv, wrapGenericCorgiJob, reportToCorgi, Status, RESOURCES, IO, readScript, PDF_OR_WEB, randId, RANDOM_DEV_CODEVERSION_PREFIX, taskMaker, toDockerSourceSection, stepsToTasks } from './util'

const commonLogFile = `${IO.COMMON_LOG}/log`
const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
const genericAbortMessage = 'Job was aborted.'
const s3UploadFailMessage = 'Error occurred upload to S3.'

function makePipeline(env: KeyValue) {
    env.CODE_VERSION = process.env.CODE_VERSION
    const resources = [
        {
            name: RESOURCES.CORGI_GIT_PDF,
            type: 'corgi-resource',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_PDF,
                status_id: 1
            }
        },
        {
            name: RESOURCES.CORGI_GIT_WEB,
            type: 'corgi-resource',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_DIST_PREVIEW,
                status_id: 1
            }
        },
        {
            name: RESOURCES.CORGI_GIT_DOCX,
            type: 'corgi-resource',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_DOCX,
                status_id: 1
            }
        },
        {
            name: RESOURCES.CORGI_GIT_EPUB,
            type: 'corgi-resource',
            source: {
                api_root: env.CORGI_API_URL,
                job_type_id: JobType.GIT_EPUB,
                status_id: 1
            }
        }
    ]

    const buildPdfJob = (resource: RESOURCES, tasks: any[]) => {
        const report = reportToCorgi(resource)
        const lookupBookDef = buildLookUpBook(resource)
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, `build-pdf`, resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.ARTIFACTS}/pdf_url`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        }, {
            max_in_flight: 3
        })
    }

    const buildWebJob = (resource: RESOURCES, tasks: any[]) => {
        const report = reportToCorgi(resource)
        const lookupBookDef = buildLookUpBook(resource)
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, `web-preview`, resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.ARTIFACTS}/pdf_url`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        }, {
            max_in_flight: 3
        })

    }

    const buildGitDocxJob = (resource: RESOURCES, tasks: any[]) => {
        const report = reportToCorgi(resource)
        const lookupBookDef = buildLookUpBook(resource)
        // PDF_OR_WEB argument does not seem to actually do anything
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, `build-docx`, resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.ARTIFACTS}/pdf_url`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        }, {
            max_in_flight: 3
        })
    }

    const buildGitEpubJob = (resource: RESOURCES, tasks: any[]) => {
        const report = reportToCorgi(resource)
        const lookupBookDef = buildLookUpBook(resource)
        // PDF_OR_WEB argument does not seem to actually do anything
        const lookupBookTask = taskMaker(env, PDF_OR_WEB.PDF, lookupBookDef)
        return wrapGenericCorgiJob(env, 'build-epub', resource, {
            do: [
                report(Status.ASSIGNED, {
                    worker_version: env.CODE_VERSION
                }),
                lookupBookTask,
                report(Status.PROCESSING),
                ...tasks
            ],
            on_success: report(Status.SUCCEEDED, {
                pdf_url: `${IO.ARTIFACTS}/pdf_url`
            }),
            on_failure: report(Status.FAILED, {
                error_message_file: commonLogFile
            })
        })
    }

    const gitPdfJob = buildPdfJob(RESOURCES.CORGI_GIT_PDF, stepsToTasks(env, PDF_OR_WEB.PDF, GIT_PDF_STEPS))
    const gitWeb = buildWebJob(RESOURCES.CORGI_GIT_WEB, stepsToTasks(env, PDF_OR_WEB.WEB, GIT_WEB_STEPS))
    const gitDocx = buildGitDocxJob(RESOURCES.CORGI_GIT_DOCX, stepsToTasks(env, PDF_OR_WEB.WEB, GIT_GDOC_STEPS))
    const gitEpub = buildGitEpubJob(RESOURCES.CORGI_GIT_EPUB, stepsToTasks(env, PDF_OR_WEB.WEB, GIT_EPUB_STEPS))

    const resourceTypes = [
        {
            name: 'corgi-resource',
            type: 'docker-image',
            source: toDockerSourceSection(env)
        }
    ]

    return { jobs: [gitPdfJob, gitWeb, gitDocx, gitEpub], resources, resource_types: resourceTypes }
}

export function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    console.log(`Writing pipeline YAML file to ${saveYamlFile}`)
    fs.writeFileSync(saveYamlFile, yaml.dump(makePipeline(loadEnv(loadEnvFile))))
}

loadSaveAndDump('./env/corgi-staging.json', './corgi-staging.yml')
loadSaveAndDump('./env/corgi-production.json', './corgi-production.yml')
