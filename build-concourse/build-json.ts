import { writeFileSync } from 'fs'
import { join } from 'path'
import { STEP_MAP, ARCHIVE_WEB_STEPS, CLI_GIT_PDF_STEPS, CLI_GIT_WEB_STEPS, CLI_ARCHIVE_PDF_STEPS, CLI_ARCHIVE_GDOC_STEPS, Step } from "./step-definitions";
import { Env } from './util';

const toName = (s: Step) => s.name
const toCase = (s: string) => `IO_${s.toUpperCase().replace(/-/g, '_')}`
const mapEnv = (e: Env) => Object.entries(e).filter(([_, isRequired]) => isRequired).map(([envName]) => envName)

const steps = Array.from(STEP_MAP.entries()).map(([k, s]) => ([k, {inputDirs: s.inputs.map(toCase), outputDirs: s.outputs.map(toCase), requiredEnv: mapEnv(s.env)}]))
const json = {
    __note__: "This file is autogenerted. Do not edit it directly",
    steps: Object.fromEntries(steps),
    pipelines: {
        'all-git-pdf': CLI_GIT_PDF_STEPS.map(toName),
        'all-git-web': CLI_GIT_WEB_STEPS.map(toName),
        'all-archive-pdf': CLI_ARCHIVE_PDF_STEPS.map(toName),
        'all-archive-web': ARCHIVE_WEB_STEPS.map(toName),
        'all-archive-gdoc': CLI_ARCHIVE_GDOC_STEPS.map(toName),
    }
}

writeFileSync(join(__dirname, '../step-config.json'), JSON.stringify(json, null, 4))