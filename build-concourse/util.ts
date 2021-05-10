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


export type Env = { [key: string]: string | number }
export type DockerDetails = {
    repository: string
    tag: string
    username?: string
    password?: string
    corgiApiUrl: string
}

type TaskArgs = {
    resource: string
    apiRoot: string
    processingStates: Status[]
    completedStates: Status[]
    abortedStates: Status[]
}

const bashy = (cmd: string) => ({
    path: '/bin/bash',
    args: ['-cxe', `source /openstax/venv/bin/activate\n${cmd}`]
})
export const pipeliney = (docker: DockerDetails, env: Env, taskName: string, cmd: string, inputs: string[], outputs: string[]) => ({
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
        params: env,
        run: bashy(cmd),
        inputs: inputs.map(name => ({ name })),
        outputs: outputs.map(name => ({ name })),
    }
})

const reportToOutputProducer = (resource: string) => {
    return (status: number, extras: any) => {
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

const taskStatusCheck = (docker, taskArgs: TaskArgs) => {
    const { resource, apiRoot, processingStates, completedStates, abortedStates } = taskArgs

    const toBashCaseMatch = (list: Status[]) => {
        return `@(${list.join('|')})`
    }

    const env = {
        RESOURCE: resource,
        API_ROOT: apiRoot,
        PROCESSING_STATES: toBashCaseMatch(processingStates),
        COMPLETED_STATES: toBashCaseMatch(completedStates),
        ABORTED_STATES: toBashCaseMatch(abortedStates)
    }
    const cmd = dedent`#!/bin/bash
      job_id=$(cat "$RESOURCE/id")
      subsequent_failures=0
      while true; do
        curl -w "%{http_code}" -o response "$API_ROOT/jobs/$job_id" > status_code
        timestamp=$(date '+%H:%M:%S')
        status_code="$(cat status_code)"
        if [[ "$status_code" = "200" ]]; then
          subsequent_failures=0
          current_job_status_id=$(jq -r '.status.id' response)
          shopt -s extglob
          case "$current_job_status_id" in
            $PROCESSING_STATES)
              echo "$timestamp | Pipeline running, no intervention needed"
              ;;
            $COMPLETED_STATES)
              echo "$timestamp | Pipeline completed, no intervention needed"
              sleep 1
              exit 0
              ;;
            $ABORTED_STATES)
              echo "$timestamp | Job aborted via UI, torpedoing the build"
              sleep 1
              exit 1
              ;;
            *)
              echo "$timestamp | Unknown job status id ('$current_job_status_id'), torpedoing the build"
              sleep 1
              exit 1
              ;;
          esac
        elif [[ "$((++subsequent_failures))" -gt "2" ]]; then
          echo "$timestamp | Unable to check status code ('$status_code'), torpedoing the build"
          sleep 1
          exit 1
        fi
        sleep 30
      done
      `
    const inputs = [resource]
    return pipeliney(docker, env, 'status-check', cmd, inputs, [])
}

const runWithStatusCheck = (docker: DockerDetails, resource, step) => {
    const reporter = reportToOutputProducer(resource)
    return {
        in_parallel: {
            fail_fast: true,
            steps: [
                step,
                {
                    do: [
                        taskStatusCheck(docker, {
                            resource: resource,
                            apiRoot: docker.corgiApiUrl,
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

export const wrapGenericCorgiJob = (docker: DockerDetails, jobName: string, resource: string, step) => {
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
            runWithStatusCheck(docker, resource, step)
        ],
        on_error: report(Status.FAILED, {
            error_message: genericErrorMessage
        }),
        on_abort: report(Status.ABORTED, {
            error_message: genericAbortMessage
        })
    }
}
