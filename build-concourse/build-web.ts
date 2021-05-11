import * as fs from 'fs'
import * as dedent from 'dedent'
import * as yaml from 'js-yaml'
import { devOrProductionSettings, IN_OUT, populateEnv, RESOURCES, toConcourseTask } from './util'

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
        toConcourseTask('dequeue-book', [RESOURCES.S3_QUEUE], [IN_OUT.BOOK], { CONTENT_SOURCE }, dedent`
            exec 2> >(tee ${IN_OUT.BOOK}/stderr >&2)
            book="${RESOURCES.S3_QUEUE}/${env.codeVersion}.web-hosting-queue.json"
            if [[ ! -s "$book" ]]; then
                echo "Book is empty"
                exit 1
            fi

            case $CONTENT_SOURCE in
                archive)
                    echo -n "$(cat $book | jq -er '.collection_id')" >${IN_OUT.BOOK}/collection_id
                    echo -n "$(cat $book | jq -er '.server')" >${IN_OUT.BOOK}/server
                ;;
                git)
                    echo -n "$(cat $book | jq -r '.slug')" >${IN_OUT.BOOK}/slug
                    echo -n "$(cat $book | jq -r '.repo')" >${IN_OUT.BOOK}/repo
                ;;
                *)
                    echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
                    exit 1
                ;;
            esac

            echo -n "$(cat $book | jq -r '.style')" >${IN_OUT.BOOK}/style
            echo -n "$(cat $book | jq -r '.version')" >${IN_OUT.BOOK}/version
            echo -n "$(cat $book | jq -r '.uuid')" >${IN_OUT.BOOK}/uuid
    `),

        toConcourseTask('all-web-book', [IN_OUT.BOOK], [IN_OUT.COMMON_LOG], { AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, COLUMNS: '80' }, dedent`
            exec > >(tee ${IN_OUT.COMMON_LOG}/log >&2) 2>&1

            book_style="$(cat ./${IN_OUT.BOOK}/style)"
            book_version="$(cat ./${IN_OUT.BOOK}/version)"
            book_uuid="$(cat ./${IN_OUT.BOOK}/uuid)"

            if [[ -f ./${IN_OUT.BOOK}/repo ]]; then
                book_repo="$(cat ./${IN_OUT.BOOK}/repo)"
                book_slug="$(cat ./${IN_OUT.BOOK}/slug)"
                docker-entrypoint.sh all-git-web "$book_repo" "$book_version" "$book_style" "$book_slug"
                echo "Git upload not supported yet"
                exit 1
            else
                book_server="$(cat ./${IN_OUT.BOOK}/server)"
                book_col_id="$(cat ./${IN_OUT.BOOK}/collection_id)"
                docker-entrypoint.sh all-archive-web "$book_col_id" "$book_style" "$book_version" "$book_server"
                echo "===> Upload book"
                docker-entrypoint.sh archive-upload-book "${env.queueBucket}" "${env.codeVersion}"
            fi
`),

    ]
}

fs.writeFileSync('./build-web.yml', yaml.dump({ jobs: [feeder, webBaker], resources }))