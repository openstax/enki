import { writeFileSync } from 'fs'
import { join } from 'path'
import { STEP_MAP, CLI_GIT_PDF_STEPS, CLI_GIT_WEB_STEPS, CLI_GIT_GDOC_STEPS, Step, CLI_GIT_EPUB_STEPS } from "./step-definitions";
import { Env } from './util';

const toName = (s: Step) => s.name
const toCase = (s: string) => `IO_${s.toUpperCase().replace(/-/g, '_')}`
const mapEnv = (e: Env) => Object.entries(e).filter(([_, isRequired]) => isRequired).map(([envName]) => envName)

// Older NodeJS versions do not implement Object.fromEntries()
function fromEntries(entries: Iterable<readonly any[]>) {
    const ret = {}
    for (const entry of entries) {
        ret[entry[0]] = entry[1]
    }
    return ret
}

const stepEntries = Array.from(STEP_MAP.entries()).map(([k, s]) => ([k, {inputDirs: s.inputs.map(toCase), outputDirs: s.outputs.map(toCase), requiredEnv: mapEnv(s.env)}]))
const steps = fromEntries(stepEntries)
const json = {
    __note__: "This file is autogenerted. Do not edit it directly",
    steps,
    pipelines: {
        'all-pdf': CLI_GIT_PDF_STEPS.map(toName),
        'all-web': CLI_GIT_WEB_STEPS.map(toName),
        'all-epub': CLI_GIT_EPUB_STEPS.map(toName),
        'all-docx': CLI_GIT_GDOC_STEPS.map(toName),
    }
}

writeFileSync(join(__dirname, '../step-config.json'), JSON.stringify(json, null, 4))