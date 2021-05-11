import * as fs from 'fs'
import * as path from 'path'
import * as dedent from 'dedent'

const buildLogRetentionDays = 14
const genericErrorMessage = 'Error occurred in Concourse. See logs for details.'
const genericAbortMessage = 'Job was aborted.'
const s3UploadFailMessage = 'Error occurred upload to S3.'

export enum JobType {
    PDF = 1,
    DIST_PREVIEW = 2,
    GIT_PDF = 3,
    GIT_DIST_PREVIEW = 4
}
export enum Status {
    QUEUED = 1,
    ASSIGNED = 2,
    PROCESSING = 3,
    FAILED = 4,
    SUCCEEDED = 5,
    ABORTED = 6
}


// A Boolean value denotes that the value will be looked up from this scripts' environment and `true` indicates that it is required
export type Env = { [key: string]: string | boolean }
export type DockerDetails = {
    repository: string
    tag: string
    username?: string
    password?: string
    corgiApiUrl?: string
}

type TaskArgs = {
    resource: string
    apiRoot: string
    processingStates: Status[]
    completedStates: Status[]
    abortedStates: Status[]
}

export type Pipeline = any
export type ConcourseTask = {
    task: string
    config: {
        platform: 'linux'
        image_resource: {
            type: 'docker-image'
            source: {
                repository: string
                tag: string
                username?: string
                password?: string
            }
        },
        params: Env
        run: { path: string,
            args: string[]}
        inputs: Array<{name: string}>
        outputs: Array<{name: string}>
    }
} | {
    get: string
    trigger: boolean
    version: 'every'
}

export enum RESOURCES {
    S3_QUEUE = 's3-queue',
    TICKER = 'ticker',
    OUTPUT_PRODUCER_GIT_PDF = 'output-producer-git-pdf',
}
// Note: toConcourseTask converts these into IO_BOOK-style environment variables for the tasks to use
// so that the scripts do not have to hardcode these directories into the script file
export enum IO {
    BOOK = 'book',
    COMMON_LOG = 'common-log',
    ARTIFACTS_SINGLE = 'artifacts-single',
}

export type TaskNode = {
    inputs: IO[]
    outputs: IO[]
    staticEnv: Env
    dynamicEnvKeys: string[]
    name: string
    code: string
}

const hardCodeSomeEnvValuesWhenNotDevMode = (key: string) => {
    if (!devOrProductionSettings().isDev) {
        if (key === 'AWS_ACCESS_KEY_ID') { return '((prod-web-hosting-content-gatekeeper-access-key-id))' }
        else if (key === 'AWS_SECRET_ACCESS_KEY') { return '((prod-web-hosting-content-gatekeeper-secret-access-key))'}
    }
    return process.env[key]
}

const expect = <T>(v: T | null | undefined, message: string = 'BUG/ERROR: This value is expected to exist'): T => {
    if (v == null) {
        throw new Error(message)
    }
    return v
}
const bashy = (cmd: string) => ({
    path: '/bin/bash',
    args: ['-cxe', `source /openstax/venv/bin/activate\n${cmd}`]
})
export const populateEnv = (env: Env) => {
    const ret: any = {}
    for (const key in env) {
        const value = env[key]
        if (value === true) {
            ret[key] = expect(hardCodeSomeEnvValuesWhenNotDevMode(key), `Expected environment variable '${key}' to be set but it was not.`)
        } else if (value === false) {
            ret[key] = hardCodeSomeEnvValuesWhenNotDevMode(key)
        } else if(typeof value === 'string') {
            ret[key] = value
        } else {
            throw new Error('BUG: Unsupported type')
        }
    }
    return ret
}
const toUpperCamel = (s: string) => s.toUpperCase().replace(/-/g, '_')
const ioToEnvVars = (inputs: string[], outputs: string[]) => {
    const ret = {}
    inputs.forEach(s => ret[`IO_${toUpperCamel(s)}`] = s)
    outputs.forEach(s => ret[`IO_${toUpperCamel(s)}`] = s)
    return ret
}
export const toConcourseTask = (taskName: string, inputs: string[], outputs: string[], env: Env, cmd: string): ConcourseTask => ({
    task: taskName,
    config: {
        platform: 'linux',
        image_resource: {
            type: 'docker-image',
            source: {
                repository: docker.repository,
                tag: docker.tag,
                username: docker.username,
                password: docker.password
            }
        },
        params: {...ioToEnvVars(inputs, outputs), ...populateEnv(env)},
        run: bashy(cmd),
        inputs: inputs.map(name => ({ name })),
        outputs: outputs.map(name => ({ name })),
    }
})
export const readScript = (pathToFile: string) => `${fs.readFileSync(path.resolve(__dirname, pathToFile), { encoding: 'utf-8' })}\n# Source: ${pathToFile}`

export const reportToOutputProducer = (resource: RESOURCES) => {
    return (status: number, extras?: any) => {
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

const taskStatusCheck = (taskArgs: TaskArgs) => {
    const { resource, apiRoot, processingStates, completedStates, abortedStates } = taskArgs

    const toBashCaseMatch = (list: Status[]) => {
        return `@(${list.join('|')})`
    }

    const env = {
        RESOURCE: expect(resource),
        API_ROOT: expect(apiRoot),
        PROCESSING_STATES: toBashCaseMatch(processingStates),
        COMPLETED_STATES: toBashCaseMatch(completedStates),
        ABORTED_STATES: toBashCaseMatch(abortedStates)
    }
    return toConcourseTask('status-check', [resource], [], env, readScript('script/task_status_check.sh'))
}

const runWithStatusCheck = (resource: RESOURCES, step: Pipeline) => {
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
                            apiRoot: expect(docker.corgiApiUrl),
                            processingStates: [Status.ASSIGNED, Status.PROCESSING],
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

export const wrapGenericCorgiJob = (jobName: string, resource: RESOURCES, step: Pipeline, extraArgs?: any) => {
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
        }),
        ...extraArgs
    }
}


export enum PDF_OR_WEB {
    PDF = 'pdf',
    WEB = 'web'
  }
  export const variantMaker = (pdfOrWeb: PDF_OR_WEB) => toConcourseTask(`build-all-pdf-or-web=${pdfOrWeb}`, [IO.BOOK], [IO.COMMON_LOG, IO.ARTIFACTS_SINGLE], { AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, PDF_OR_WEB: pdfOrWeb, S3_ARTIFACTS_BUCKET: true, COLUMNS: '80' }, readScript('script/build_pdf_or_web_from_archive_or_git.sh'))
  


type Settings = { 
    queueBucket: string,
    artifactBucket: string,
    codeVersion: string,
    isDev: boolean
}

export const expectEnv = (name: string) => {
    const value = process.env[name]
    if (!value) {
        throw new Error(`Missing Environment variable: ${name}. This should only occur during dev mode`)
    }
    return value
}
const rand = (len: number) => Math.random().toString().substr(2, len)

export const devOrProductionSettings = (): Settings => {
    if (process.env['DEV_MODE'] || process.env['AWS_SESSION_TOKEN']) {
        return {
            codeVersion: `randomlocaldevtag-${rand(7)}`,
            queueBucket: 'openstax-sandbox-web-hosting-content-queue-state',
            artifactBucket: expectEnv('S3_ARTIFACTS_BUCKET'),
            isDev: true
        }
    } else {
        return {
            codeVersion: expectEnv('CODE_VERSION'),
            queueBucket: 'openstax-web-hosting-content-queue-state',
            artifactBucket: expectEnv('COPS_ARTIFACTS_S3_BUCKET'),
            isDev: false
        }
    }
}


export const docker: DockerDetails = {
    repository: process.env['DOCKER_REPOSITORY'] || 'openstax/book-pipeline',
    tag: devOrProductionSettings().isDev ? 'main' : expectEnv('CODE_VERSION'),
    username: process.env['DOCKER_USERNAME'],
    password: process.env['DOCKER_PASSWORD'],
    corgiApiUrl: devOrProductionSettings().isDev ? 'https://corgi-staging.openstax.org/api' : 'https://corgi.openstax.org/api'
}
