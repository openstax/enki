import * as fs from 'fs'
import * as dedent from 'dedent'
import * as yaml from 'js-yaml'

const CONTENT_SOURCE = 'archive'

enum RESOURCES {
    S3_QUEUE = 's3-queue',
    TICKER = 'ticker',
}
enum IN_OUT {
    BOOK = 'book',
    COMMON_LOG = 'common-log',
}

type Settings = { 
    AWS_ACCESS_KEY_ID: string,
    AWS_SECRET_ACCESS_KEY: string,
    AWS_SESSION_TOKEN?: string,
    s3Bucket: string,
    codeVersion: string,
    dockerTag: string,
    isDev: boolean
}
type Env = { [key: string]: string | number }
type DockerDetails = {
    repository: string
    username?: string,
    password?: string
}

const expectEnv = (name: string) => {
    const value = process.env[name]
    if (!value) {
        throw new Error(`Missing Environment variable: ${name}. This should only occur during dev mode`)
    }
    return value
}
const rand = (len: number) => Math.random().toString().substr(2, len)

const devOrProductionSettings = (): Settings => {
    if (process.env['DEV_MODE'] || process.env['AWS_SESSION_TOKEN']) {
        return {
            AWS_ACCESS_KEY_ID: expectEnv('AWS_ACCESS_KEY_ID'),
            AWS_SECRET_ACCESS_KEY: expectEnv('AWS_SECRET_ACCESS_KEY'),
            AWS_SESSION_TOKEN: expectEnv('AWS_SESSION_TOKEN'),
            dockerTag: '',
            codeVersion: `randomlocaldevtag-${rand(7)}`,
            s3Bucket: 'openstax-sandbox-web-hosting-content-queue-state',
            isDev: true
        }
    } else {
        return {
            AWS_ACCESS_KEY_ID: '((prod-web-hosting-content-gatekeeper-access-key-id))',
            AWS_SECRET_ACCESS_KEY: '((prod-web-hosting-content-gatekeeper-secret-access-key))',
            dockerTag: expectEnv('CODE_VERSION'),
            codeVersion: expectEnv('CODE_VERSION'),
            s3Bucket: 'openstax-web-hosting-content-queue-state',
            isDev: false
        }
    }
}

const bashy = (cmd) => ({
    path: '/bin/bash',
    args: ['-cxe', `source /openstax/venv/bin/activate\n${cmd}`]
})
const pipeliney = (docker: DockerDetails, env: Env, taskName: string, cmd: string, inputs: string[], outputs: string[]) => ({
    task: taskName,
    config: {
        platform: 'linux',
        image_resource: {
            type: 'docker-image',
            source: {
                repository: docker.repository,
                tag: env.dockerTag,
                username: docker.username,
                password: docker.password
            }
        },
        params: env,
        run: bashy(cmd),
        inputs: inputs.map(name => ({ name })),
        outputs: outputs.map(name => ({ name })),
    }
})

const docker: DockerDetails = {
    repository: process.env['DOCKER_REPOSITORY'] || 'openstax/book-pipeline',
}
const env = devOrProductionSettings()

const resources = [
    {
        name: RESOURCES.S3_QUEUE,
        source: {
            access_key_id: env.AWS_ACCESS_KEY_ID,
            secret_access_key: env.AWS_SECRET_ACCESS_KEY,
            session_token: env.AWS_SESSION_TOKEN,
            bucket: env.s3Bucket,
            initial_version: 'initializing',
            versioned_file: `${env.codeVersion}.web-hosting-queue.json`
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
    }, pipeliney(docker, {AWS_ACCESS_KEY_ID: env.AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY: env.AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN: env.AWS_SESSION_TOKEN}, 'check-feed', dedent`
            curl https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json -o book-feed.json
            check-feed book-feed.json "${env.codeVersion}" "${env.s3Bucket}" "${env.codeVersion}.web-hosting-queue.json" "50" "archive-dist" "archive"
        `, [], []),
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
        pipeliney(docker, { CONTENT_SOURCE }, 'dequeue-book', dedent`
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
    `, [RESOURCES.S3_QUEUE], [IN_OUT.BOOK]),

        pipeliney(docker, { COLUMNS: 80 }, 'all-web-book', dedent`
            exec > >(tee ${IN_OUT.COMMON_LOG}/log >&2) 2>&1

            book_style="$(cat ./${IN_OUT.BOOK}/style)"
            book_version="$(cat ./${IN_OUT.BOOK}/version)"
            book_uuid="$(cat ./${IN_OUT.BOOK}/uuid)"

            if [[ -f ./${IN_OUT.BOOK}/repo ]]; then
                book_repo="$(cat ./${IN_OUT.BOOK}/repo)"
                book_slug="$(cat ./${IN_OUT.BOOK}/slug)"
                docker-entrypoint.sh all-git-web "$book_repo" "$book_version" "$book_style" "$book_slug"
            else
                book_server="$(cat ./${IN_OUT.BOOK}/server)"
                book_col_id="$(cat ./${IN_OUT.BOOK}/collection_id)"
                docker-entrypoint.sh all-archive-web "$book_col_id" "$book_style" "$book_version" "$book_server"
            fi
`, [IN_OUT.BOOK], [IN_OUT.COMMON_LOG])
    ]
}

fs.writeFileSync('./build-web.yml', yaml.dump({ jobs: [feeder, webBaker], resources }))