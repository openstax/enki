import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { KeyValue, loadEnv, randId, RANDOM_DEV_CODEVERSION_PREFIX, readScript, RESOURCES, toConcourseTask, expect, taskMaker, PDF_OR_WEB, stepsToTasks } from './util'
import { ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD, GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD } from './step-definitions'

const CONTENT_SOURCE = 'archive'

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
    
    const archiveFeeder = {
        name: 'archive-feeder',
        plan: [{
            get: RESOURCES.TICKER,
            trigger: true,
        }, toConcourseTask(envValues, 'archive-check-feed', [], [], {AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, WEB_FEED_FILE_URL: true, CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, MAX_BOOKS_PER_TICK: true}, readScript('script/archive_check_feed.sh')),
        ]
    }
    
    const archiveWebBaker = {
        name: 'archive-bakery',
        max_in_flight: expect(envValues.MAX_INFLIGHT_JOBS),
        plan: [
            {
                get: RESOURCES.S3_QUEUE,
                trigger: true,
                version: 'every'
            },
            ...stepsToTasks(envValues, PDF_OR_WEB.WEB, ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD),
        ]
    }

    const gitFeeder = {
        name: 'git-feeder',
        plan: [{
            get: RESOURCES.TICKER,
            trigger: true,
        }, toConcourseTask(envValues, 'git-check-feed', [], [], {AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, WEB_FEED_FILE_URL: true, CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, MAX_BOOKS_PER_TICK: true}, readScript('script/git_check_feed.sh')),
        ]
    }
    
    const gitWebBaker = {
        name: 'git-bakery',
        max_in_flight: expect(envValues.MAX_INFLIGHT_JOBS),
        plan: [
            {
                get: RESOURCES.S3_QUEUE,
                trigger: true,
                version: 'every'
            },
            ...stepsToTasks(envValues, PDF_OR_WEB.WEB, GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD),
        ]
    }

    return { jobs: [archiveFeeder, archiveWebBaker, gitFeeder, gitWebBaker], resources }
}

export function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    console.log(`Writing pipeline YAML file to ${saveYamlFile}`)
    fs.writeFileSync(saveYamlFile, yaml.dump(makePipeline(loadEnv(loadEnvFile))))
}

loadSaveAndDump('./env/webhosting-sandbox.json', './webhosting-sandbox.yml')
loadSaveAndDump('./env/webhosting-production.json', './webhosting-production.yml')
