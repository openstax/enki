import * as fs from 'fs'
import * as dedent from 'dedent'
import * as yaml from 'js-yaml'
import { devOrProductionSettings, IO, populateEnv, readScript, RESOURCES, toConcourseTask } from './util'

const CONTENT_SOURCE = 'archive'

const env = devOrProductionSettings()
const myEnv = populateEnv({AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false})
const resources = [
    {
        name: RESOURCES.S3_QUEUE,
        source: {
            access_key_id: myEnv.AWS_ACCESS_KEY_ID,
            secret_access_key: myEnv.AWS_SECRET_ACCESS_KEY,
            session_token: myEnv.AWS_SESSION_TOKEN,
            bucket: devOrProductionSettings().queueBucket,
            initial_version: 'initializing',
            versioned_file: `${devOrProductionSettings().codeVersion}.web-hosting-queue.json`
        },
        type: 's3',
    },
    {
        type: 'time',
        name: RESOURCES.TICKER,
        source: {
            interval: '12h'
        }
    }
]

const feeder = {
    name: 'feeder',
    plan: [{
        get: RESOURCES.TICKER,
        trigger: true,
    }, toConcourseTask('check-feed', [], [], {AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}, dedent`
            curl https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json -o book-feed.json
            check-feed book-feed.json "${env.codeVersion}" "${env.queueBucket}" "${env.codeVersion}.web-hosting-queue.json" "50" "archive-dist" "archive"
        `),
    ]
}

const webBaker = {
    name: 'bakery',
    max_in_flight: env.isDev ? 2 : 5,
    plan: [
        {
            get: RESOURCES.S3_QUEUE,
            trigger: true,
            version: 'every'
        },
        toConcourseTask('dequeue-book', [RESOURCES.S3_QUEUE], [IO.BOOK], { CONTENT_SOURCE, S3_QUEUE: RESOURCES.S3_QUEUE, CODE_VERSION: env.codeVersion }, readScript('script/dequeue_book.sh')),
        toConcourseTask('all-web-book', [IO.BOOK], [IO.COMMON_LOG], { AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, CODE_VERSION: env.codeVersion, CORGI_ARTIFACTS_S3_BUCKET: env.artifactsBucket, COLUMNS: '80' }, readScript('script/all_web_book.sh')),
    ]
}

fs.writeFileSync('./build-web.yml', yaml.dump({ jobs: [feeder, webBaker], resources }))