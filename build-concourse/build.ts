import * as dedent from 'dedent'
import * as yaml from 'js-yaml'

const DOCKER_REPOSITORY = 'openstax/pipeline'
const CONTENT_SOURCE = 'archive'

enum IN_OUT {
    S3_QUEUE = 's3-queue',
    BOOK = 'book',
    COMMON_LOG = 'common-log',
}

type Env = { [key: string]: string | number }
type DockerDetails = {
    tag: string,
    username?: string,
    password?: string
}

const bashy = (cmd) => ({
    path: '/bin/bash',
    args: ['-cxe', cmd]
})
const pipeliney = (docker: DockerDetails, env: Env, taskName: string, cmd: string, inputs: string[], outputs: string[]) => ({
    task: taskName,
    config: {
        platform: 'linux',
        image_resource: {
            type: 'docker-image',
            source: {
                repository: DOCKER_REPOSITORY,
                tag: docker.tag,
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

const docker = {
    tag: '20210421.141058'
}
const env = {
    AWS_ACCESS_KEY_ID: '((prod-web-hosting-content-gatekeeper-access-key-id))',
    AWS_SECRET_ACCESS_KEY: '((prod-web-hosting-content-gatekeeper-secret-access-key))'
}

const feeder = {
    name: 'feeder',
    plan: [{
        get: 'ticker',
        trigger: true,
    }, pipeliney(docker, env, 'check-feed', dedent`
            curl https://raw.githubusercontent.com/openstax/content-manager-approved-books/master/approved-book-list.json -o book-feed.json
            check-feed book-feed.json "${docker.tag}" "openstax-web-hosting-content-queue-state" "${docker.tag}.web-hosting-queue.json" "50" "archive-dist" "archive"
        `, [], []),
    ]
}

const baker = {
    name: 'bakery',
    max_in_flight: 5,
    plan: [
        {
            get: IN_OUT.S3_QUEUE,
            trigger: true,
            version: 'every'
        },
        pipeliney(docker, { CONTENT_SOURCE }, 'dequeue-book', dedent`
            exec 2> >(tee book/stderr >&2)
            book="s3-queue/${docker.tag}.web-hosting-queue.json"
            if [[ ! -s "$book" ]]; then
                echo "Book is empty"
                exit 1
            fi

            case $CONTENT_SOURCE in
                archive)
                    echo -n "$(cat $book | jq -er '.collection_id')" >book/collection_id
                    echo -n "$(cat $book | jq -er '.server')" >book/server
                ;;
                git)
                    echo -n "$(cat $book | jq -r '.slug')" >book/slug
                    echo -n "$(cat $book | jq -r '.repo')" >book/repo
                ;;
                *)
                    echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
                    exit 1
                ;;
            esac

            echo -n "$(cat $book | jq -r '.style')" >book/style
            echo -n "$(cat $book | jq -r '.version')" >book/version
            echo -n "$(cat $book | jq -r '.uuid')" >book/uuid
    `, [IN_OUT.S3_QUEUE], [IN_OUT.BOOK]),

        pipeliney(docker, { COLUMNS: 80 }, 'archive-pdf-book', dedent`
            exec > >(tee common-log/log >&2) 2>&1

            book_style="$(cat ./book/style)"
            book_version="$(cat ./book/version)"
            book_uuid="$(cat ./book/uuid)"

            if [[ -f ./book/repo ]]; then
                book_repo="$(cat ./book/repo)"
                book_slug="$(cat ./book/slug)"
                docker-entrypoint.sh all-git-pdf "$book_repo" "$book_version" "$book_style" "$book_slug"
            else
                book_server="$(cat ./book/server)"
                book_col_id="$(cat ./book/collection_id)"
                docker-entrypoint.sh all-archive-pdf "$book_col_id" "$book_style" "$book_version" "$book_server"
            fi
`, [IN_OUT.BOOK], [IN_OUT.COMMON_LOG])
    ]
}

console.log(yaml.dump({ jobs: [feeder, baker] }))