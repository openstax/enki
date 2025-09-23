import * as fs from "fs";
import * as yaml from "js-yaml";
import {
    KeyValue,
    loadEnv,
    readScript,
    RESOURCES,
    toConcourseTask,
    expect,
    stepsToTasks,
    reportToSlack,
    RESOURCE_TYPES,
    ConcourseTask,
    SlackNotifyOptions,
} from "./util";
import { GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD } from "./step-definitions";

function makePipeline(envValues: KeyValue) {
    const resourceTypes: {
        name: string
        type: string
        source: Record<string, any>
    }[] = []
    const resources: {
        name: string
        source: Record<string, any>
        type: string
    }[] = [
        {
            name: RESOURCES.S3_GIT_QUEUE,
            source: {
                access_key_id: envValues.AWS_ACCESS_KEY_ID,
                secret_access_key: envValues.AWS_SECRET_ACCESS_KEY,
                session_token: envValues.AWS_SESSION_TOKEN,
                bucket: envValues.WEB_QUEUE_STATE_S3_BUCKET,
                initial_version: "initializing",
                versioned_file: `${envValues.CODE_VERSION}.${envValues.QUEUE_SUFFIX}`,
            },
            type: "s3",
        },
        {
            type: "time",
            name: RESOURCES.TICKER,
            source: {
                interval: envValues.PIPELINE_TICK_INTERVAL,
            },
        },
    ];

    const gitFeeder = {
        name: "git-feeder",
        plan: [
            {
                get: RESOURCES.TICKER,
                trigger: true,
            },
            toConcourseTask(
                envValues,
                "check-feed",
                [],
                [],
                {
                    AWS_ACCESS_KEY_ID: true,
                    AWS_SECRET_ACCESS_KEY: true,
                    AWS_SESSION_TOKEN: false,
                    CORGI_API_URL: true,
                    CODE_VERSION: true,
                    WEB_QUEUE_STATE_S3_BUCKET: true,
                    MAX_BOOKS_PER_TICK: true,
                    STATE_PREFIX: true,
                    QUEUE_SUFFIX: true,
                    SLACK_WEBHOOK_CE_STREAM: false,
                    SLACK_POST_PARAMS: false,
                },
                readScript("script/check_feed.sh")
            ),
        ],
    };

    const gitWebBaker: {
        name: string
        max_in_flight: number
        plan: ConcourseTask[]
        on_failure?: {
            put: RESOURCES;
            params: SlackNotifyOptions;
        }
    } = {
        name: "git-bakery",
        max_in_flight: expect(envValues.MAX_INFLIGHT_JOBS),
        plan: [
            {
                get: RESOURCES.S3_GIT_QUEUE,
                trigger: true,
                version: "every",
            },
            ...stepsToTasks(
                envValues,
                GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD
            ),
        ],
    };

    if (envValues.SLACK_WEBHOOK_CE_STREAM) {
        const reporter = reportToSlack(RESOURCES.SLACK_CE_STREAM)
        resourceTypes.push({
            name: RESOURCE_TYPES.SLACK_NOTIFY,
            type: "registry-image",
            source: {
                repository: "arbourd/concourse-slack-alert-resource"
            }
        });
        resources.push({
            name: RESOURCES.SLACK_CE_STREAM,
            source: {
                url: envValues.SLACK_WEBHOOK_CE_STREAM,
            },
            type: RESOURCE_TYPES.SLACK_NOTIFY
        });
        gitWebBaker.on_failure = reporter({ alert_type: 'failed' })
    }

    return {
        jobs: [gitFeeder, gitWebBaker],
        resources,
        ...(resourceTypes.length > 0
            ? { resource_types: resourceTypes }
            : undefined
        ),
    };
}

export function loadSaveAndDump(loadEnvFile: string, saveYamlFile: string) {
    console.log(`Writing pipeline YAML file to ${saveYamlFile}`);
    fs.writeFileSync(
        saveYamlFile,
        yaml.dump(makePipeline(loadEnv(loadEnvFile)))
    );
}

loadSaveAndDump("./env/webhosting-sandbox.json", "./webhosting-sandbox.yml");
loadSaveAndDump(
    "./env/webhosting-production.json",
    "./webhosting-production.yml"
);
