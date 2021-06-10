import * as fs from 'fs'
import * as dedent from 'dedent'
import * as yaml from 'js-yaml'
import { IO, KeyValue, loadEnv, randId, RANDOM_DEV_CODEVERSION_PREFIX, readScript, RESOURCES, toConcourseTask, expect, archiveTaskMaker, PDF_OR_WEB } from './util'
import { ARCHIVE_WEB_STEPS, buildUploadStep } from './step-definitions'

const CONTENT_SOURCE = 'archive'

const archiveStepsWithUpload = [...ARCHIVE_WEB_STEPS, buildUploadStep(false, true)]

function makePipeline(envValues: KeyValue) {
    const resources = [
        {
            name: RESOURCES.S3_QUEUE,
            source: {
                access_key_id: envValues.AWS_ACCESS_KEY_ID,
                secret_access_key: envValues.AWS_SECRET_ACCESS_KEY,
                session_token: envValues.AWS_SESSION_TOKEN,
                bucket: envValues.WEB_QUEUE_STATE_S3_BUCKET,
                initial_version: 'initializing',
                versioned_file: `${envValues.CODE_VERSION}.web-hosting-queue.json`
            },
            type: 's3',
        },
        {
            type: 'time',
            name: RESOURCES.TICKER,
            source: {
                interval: envValues.PIPELINE_TICK_INTERVAL
            }
        }
    ]
    
    const feeder = {
        name: 'feeder',
        plan: [{
            get: RESOURCES.TICKER,
            trigger: true,
        }, toConcourseTask(envValues, 'check-feed', [], [], {AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, WEB_FEED_FILE_URL: true, CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, MAX_BOOKS_PER_TICK: true}, readScript('script/check_feed.sh')),
        ]
    }
    
    const webBaker = {
        name: 'bakery',
        max_in_flight: expect(envValues.MAX_INFLIGHT_JOBS),
        plan: [
            {
                get: RESOURCES.S3_QUEUE,
                trigger: true,
                version: 'every'
            },
            toConcourseTask(envValues, 'dequeue-book', [RESOURCES.S3_QUEUE], [IO.BOOK], { CONTENT_SOURCE, S3_QUEUE: RESOURCES.S3_QUEUE, CODE_VERSION: true }, readScript('script/dequeue_book.sh')),
            ...archiveStepsWithUpload.map(({name,inputs,outputs,env}) => archiveTaskMaker(envValues, PDF_OR_WEB.WEB, name, inputs, outputs, env)),
        ]
    }
    return { jobs: [feeder, webBaker], resources }
}


fs.writeFileSync('./webhosting-sandbox.yml', yaml.dump(makePipeline(loadEnv('./env/webhosting-sandbox.json'))))
fs.writeFileSync('./webhosting-production.yml', yaml.dump(makePipeline(loadEnv('./env/webhosting-production.json'))))

process.env['CODE_VERSION'] = `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
fs.writeFileSync('./webhosting-local.yml', yaml.dump(makePipeline(loadEnv('./env/webhosting-local.json'))))
