import * as fs from 'fs'
import * as dedent from 'dedent'
import * as yaml from 'js-yaml'
import { IO, KeyValue, loadEnv, randId, RANDOM_DEV_CODEVERSION_PREFIX, readScript, RESOURCES, toConcourseTask } from './util'

const CONTENT_SOURCE = 'archive'

function makePipeline(env: KeyValue) {
    const resources = [
        {
            name: RESOURCES.S3_QUEUE,
            source: {
                access_key_id: env.AWS_ACCESS_KEY_ID,
                secret_access_key: env.AWS_SECRET_ACCESS_KEY,
                session_token: env.AWS_SESSION_TOKEN,
                bucket: env.WEB_QUEUE_STATE_S3_BUCKET,
                initial_version: 'initializing',
                versioned_file: `${env.CODE_VERSION}.web-hosting-queue.json`
            },
            type: 's3',
        },
        {
            type: 'time',
            name: RESOURCES.TICKER,
            source: {
                interval: env.PIPELINE_TICK_INTERVAL
            }
        }
    ]
    
    const feeder = {
        name: 'feeder',
        plan: [{
            get: RESOURCES.TICKER,
            trigger: true,
        }, toConcourseTask(env, 'check-feed', [], [], {AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, WEB_FEED_FILE_URL: true, CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, MAX_BOOKS_PER_TICK: true}, dedent`
                curl "$WEB_FEED_FILE_URL" -o book-feed.json
                check-feed book-feed.json "$CODE_VERSION" "$WEB_QUEUE_STATE_S3_BUCKET" "$CODE_VERSION.web-hosting-queue.json" "$MAX_BOOKS_PER_TICK" "archive-dist" "archive"
            `),
        ]
    }
    
    const webBaker = {
        name: 'bakery',
        max_in_flight: env.MAX_INFLIGHT_JOBS,
        plan: [
            {
                get: RESOURCES.S3_QUEUE,
                trigger: true,
                version: 'every'
            },
            toConcourseTask(env, 'dequeue-book', [RESOURCES.S3_QUEUE], [IO.BOOK], { CONTENT_SOURCE, S3_QUEUE: RESOURCES.S3_QUEUE, CODE_VERSION: true }, readScript('script/dequeue_book.sh')),
            toConcourseTask(env, 'all-web-book', [IO.BOOK], [IO.COMMON_LOG], { AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, CODE_VERSION: true, WEB_S3_BUCKET: true, GH_SECRET_CREDS: false, COLUMNS: '80' }, readScript('script/all_web_book.sh')),
        ]
    }
    return { jobs: [feeder, webBaker], resources }
}


fs.writeFileSync('./webhost-sandbox.yml', yaml.dump(makePipeline(loadEnv('./env/webhost-sandbox.json'))))
fs.writeFileSync('./webhost-production.yml', yaml.dump(makePipeline(loadEnv('./env/webhost-production.json'))))

process.env['CODE_VERSION'] = `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
fs.writeFileSync('./webhost-local.yml', yaml.dump(makePipeline(loadEnv('./env/webhost-local.json'))))
