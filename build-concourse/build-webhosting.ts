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
} from "./util";
import { GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD } from "./step-definitions";

function makePipeline(envValues: KeyValue) {
    const resources = [
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
                },
                readScript("script/check_feed.sh")
            ),
        ],
    };

    const gitWebBaker = {
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

    return { jobs: [gitFeeder, gitWebBaker], resources };
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
