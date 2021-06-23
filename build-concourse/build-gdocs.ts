import * as fs from 'fs'
import * as yaml from 'js-yaml'
import { ARCHIVE_GDOC_STEPS, buildLookUpBook, GIT_OR_ARCHIVE } from './step-definitions'
import { KeyValue, JobType, toConcourseTask, loadEnv, wrapGenericCorgiJob, reportToOutputProducer, Status, RESOURCES, IO, readScript, PDF_OR_WEB, randId, RANDOM_DEV_CODEVERSION_PREFIX, taskMaker, toDockerSourceSection, expect, stepsToTasks } from './util'

function makePipeline(envValues: KeyValue) {
    envValues.CODE_VERSION = process.env.CODE_VERSION

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

    const gdocBaker = {
        name: 'bakery',
        max_in_flight: expect(envValues.MAX_INFLIGHT_JOBS),
        plan: [
            {
                get: RESOURCES.S3_QUEUE,
                trigger: true,
                version: 'every'
            },
            ...stepsToTasks(envValues, PDF_OR_WEB.WEB, ARCHIVE_GDOC_STEPS),
        ]
    }
    return { jobs: [feeder, gdocBaker], resources }
}

function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    console.log(`Writing pipeline YAML file to ${saveYamlFile}`)
    fs.writeFileSync(saveYamlFile, yaml.dump(makePipeline(loadEnv(loadEnvFile))))
}

loadSaveAndDump('./env/gdocs-production.json', './gdocs-production.yml')

process.env['CODE_VERSION'] = `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
loadSaveAndDump('./env/gdocs-local.json', './gdocs-local.yml')
