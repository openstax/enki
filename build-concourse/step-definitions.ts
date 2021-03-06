import { Env, IO, RESOURCES } from "./util";

export enum GIT_OR_ARCHIVE {
    GIT = 'git',
    ARCHIVE = 'archive'
}

export type Step = {
    name: string
    inputs: string[]
    outputs: string[]
    env: Env
}

export const STEP_MAP = new Map<string, Step>()

function get(stepName: string) {
    /* istanbul ignore if */
    if (!STEP_MAP.has(stepName)) {
        throw new Error(`BUG: Missing step named '${stepName}'`)
    }
    return STEP_MAP.get(stepName)
}

function set(step: Step) {
    /* istanbul ignore if */
    if (STEP_MAP.has(step.name)) {
        throw new Error(`BUG: Step already added '${step.name}'`)
    } else {
        STEP_MAP.set(step.name, step)
    }
}

// ARCHIVE_WEB_STEPS
set({name: 'archive-fetch', inputs: [IO.BOOK], outputs: [IO.ARCHIVE_FETCHED], env: {}})
set({name: 'archive-fetch-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_FETCHED], env: {ABL_FILE_URL: true}})
set({name: 'archive-validate-cnxml', inputs: [IO.ARCHIVE_FETCHED], outputs: [], env: {}})
set({name: 'archive-assemble', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-assemble-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-link-extras', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-bake', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-bake-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-validate-xhtml-mathified', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-checksum', inputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-disassemble', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-patch-disassembled-links', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-jsonify', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_JSONIFIED, IO.ARTIFACTS], env: {}})
set({name: 'archive-validate-xhtml-jsonify', inputs: [IO.BOOK, IO.ARCHIVE_JSONIFIED], outputs: [], env: {}})

// GIT_PDF_STEPS
set({name: 'git-fetch', inputs: [IO.BOOK], outputs: [IO.FETCHED], env: {GH_SECRET_CREDS: false, LOCAL_SIDELOAD_REPO_PATH: false}})
set({name: 'git-fetch-metadata', inputs: [IO.BOOK, IO.FETCHED], outputs: [IO.FETCH_META, IO.RESOURCES, IO.UNUSED_RESOURCES], env: {}})
set({name: 'git-validate-cnxml', inputs: [IO.FETCHED], outputs: [], env: {}})
set({name: 'git-assemble', inputs: [IO.BOOK, IO.FETCH_META], outputs: [IO.ASSEMBLED], env: {}})
set({name: 'git-validate-references', inputs: [IO.BOOK, IO.ASSEMBLED, IO.RESOURCES], outputs: [], env: {}})
set({name: 'git-assemble-meta', inputs: [IO.BOOK, IO.ASSEMBLED], outputs: [IO.ASSEMBLE_META], env: {}})
set({name: 'git-bake', inputs: [IO.BOOK, IO.FETCHED, IO.ASSEMBLED], outputs: [IO.BAKED], env: {}})
set({name: 'git-bake-meta', inputs: [IO.BOOK, IO.ASSEMBLE_META, IO.BAKED], outputs: [IO.BAKE_META], env: {}})
set({name: 'git-validate-xhtml-mathified', inputs: [IO.BOOK, IO.MATHIFIED], outputs: [], env: {}})
set({name: 'git-link', inputs: [IO.BOOK, IO.BAKED, IO.BAKE_META], outputs: [IO.LINKED], env: {}})
set({name: 'git-mathify', inputs: [IO.BOOK, IO.LINKED, IO.BAKED], outputs: [IO.MATHIFIED], env: {}})
set({name: 'git-link-rex', inputs: [IO.BOOK, IO.MATHIFIED, IO.FETCHED, IO.FETCH_META], outputs: [IO.REX_LINKED], env: {}})
set({name: 'git-pdfify', inputs: [IO.BOOK, IO.REX_LINKED, IO.RESOURCES], outputs: [IO.ARTIFACTS], env: {}})
set({name: 'git-pdfify-meta', inputs: [IO.BOOK, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true}})

// GIT_WEB_STEPS
set({name: 'git-disassemble', inputs: [IO.BOOK, IO.LINKED, IO.BAKE_META], outputs: [IO.DISASSEMBLED], env: {}})
set({name: 'git-patch-disassembled-links', inputs: [IO.BOOK, IO.DISASSEMBLED], outputs: [IO.DISASSEMBLE_LINKED], env: {}})
set({name: 'git-jsonify', inputs: [IO.BOOK, IO.FETCHED, IO.RESOURCES, IO.DISASSEMBLE_LINKED], outputs: [IO.JSONIFIED], env: {}})
set({name: 'git-validate-xhtml-jsonify', inputs: [IO.BOOK, IO.JSONIFIED], outputs: [], env: {}})
set({name: 'git-upload-book', inputs: [IO.BOOK, IO.JSONIFIED, IO.RESOURCES], outputs: [IO.ARTIFACTS], env: {CODE_VERSION: true, CORGI_ARTIFACTS_S3_BUCKET: true, PREVIEW_APP_URL_PREFIX: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// GIT_GDOC_STEPS
set({name: 'git-gdocify', inputs: [IO.BOOK, IO.FETCH_META, IO.JSONIFIED, IO.DISASSEMBLE_LINKED, IO.RESOURCES], outputs: [IO.GDOCIFIED], env: {}})
set({name: 'git-convert-docx', inputs: [IO.BOOK, IO.GDOCIFIED], outputs: [IO.DOCX], env: {}})
set({name: 'git-docx-meta', inputs: [IO.BOOK, IO.DOCX], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true}})

// ARCHIVE_PDF_STEPS
set({name: 'archive-mathify', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-link-rex', inputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_BOOK], env: {}})
set({name: 'archive-pdf', inputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARTIFACTS], env: {}})
set({name: 'archive-pdf-metadata', inputs: [IO.BOOK, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true}})

// Concourse-specific steps
set({name: 'archive-dequeue-book', inputs: [RESOURCES.S3_ARCHIVE_QUEUE], outputs: [IO.BOOK], env: { S3_QUEUE: RESOURCES.S3_ARCHIVE_QUEUE, CODE_VERSION: true }})
set({name: 'archive-report-book-complete', inputs: [IO.BOOK], outputs: [], env: {CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})
set({name: 'git-dequeue-book', inputs: [RESOURCES.S3_GIT_QUEUE], outputs: [IO.BOOK], env: { S3_QUEUE: RESOURCES.S3_GIT_QUEUE, CODE_VERSION: true }})
set({name: 'git-report-book-complete', inputs: [IO.BOOK], outputs: [], env: {CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

set(buildArchiveUploadStep(false, false))

// These are used both by CORGI when building a preview and by the webhosting pipeline
export const ARCHIVE_WEB_STEPS = [
    get('archive-fetch'),
    get('archive-fetch-metadata'),
    // get('archive-validate-cnxml'),
    get('archive-assemble'),
    get('archive-assemble-metadata'),
    get('archive-link-extras'),
    get('archive-bake'),
    get('archive-bake-metadata'),
    get('archive-checksum'),
    get('archive-disassemble'),
    get('archive-patch-disassembled-links'),
    get('archive-jsonify'),
    get('archive-validate-xhtml-jsonify'),
]

export const CLI_GIT_PDF_STEPS = [
    get('git-fetch'),
    get('git-fetch-metadata'),
    // get('git-validate-cnxml'),
    get('git-assemble'),
    get('git-assemble-meta'),
    get('git-validate-references'),
    get('git-bake'),
    get('git-bake-meta'),
    get('git-link'),
    get('git-mathify'),
    get('git-validate-xhtml-mathified'),
    get('git-link-rex'),
    get('git-pdfify'),
]
export const GIT_PDF_STEPS = [
    ...CLI_GIT_PDF_STEPS,
    get('git-pdfify-meta'),
]

export const CLI_GIT_WEB_STEPS = [
    get('git-fetch'),
    get('git-fetch-metadata'),
    // get('git-validate-cnxml'),
    get('git-assemble'),
    get('git-assemble-meta'),
    get('git-validate-references'),
    get('git-bake'),
    get('git-bake-meta'),
    get('git-link'),
    get('git-disassemble'),
    get('git-patch-disassembled-links'),
    get('git-jsonify'),
    get('git-validate-xhtml-jsonify'),
]
export const GIT_WEB_STEPS = [
    ...CLI_GIT_WEB_STEPS,
    get('git-upload-book'),
]

export const CLI_GIT_GDOC_STEPS = [
    ...CLI_GIT_WEB_STEPS,
    get('git-gdocify'),
    get('git-convert-docx'),
]

export const GIT_GDOC_STEPS = [
    ...CLI_GIT_GDOC_STEPS,
    get('git-docx-meta'),
]

export const CLI_ARCHIVE_PDF_STEPS = [
    get('archive-fetch'),
    get('archive-fetch-metadata'), // used by archive-link-rex
    // get('archive-validate-cnxml'),
    get('archive-assemble'),
    get('archive-link-extras'),
    get('archive-bake'),
    get('archive-mathify'),
    get('archive-validate-xhtml-mathified'),
    get('archive-link-rex'),
    get('archive-pdf'),
]
export const ARCHIVE_PDF_STEPS = [
    ...CLI_ARCHIVE_PDF_STEPS,
    get('archive-pdf-metadata'),
]

function buildArchiveUploadStep(requireCorgiBucket: boolean, requireWebhostingBucket: boolean) {
    return {name: 'archive-upload-book', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_JSONIFIED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_UPLOAD], env: {CORGI_ARTIFACTS_S3_BUCKET: requireCorgiBucket, WEB_S3_BUCKET: requireWebhostingBucket, PREVIEW_APP_URL_PREFIX: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}}
}

export function buildLookUpBook(inputSource: RESOURCES): Step {
    return {name: 'look-up-book', inputs: [inputSource], outputs: [IO.BOOK, IO.COMMON_LOG], env: { INPUT_SOURCE_DIR: inputSource }}
}

export const ARCHIVE_WEB_STEPS_WITH_UPLOAD = [...ARCHIVE_WEB_STEPS, buildArchiveUploadStep(true, false)]

export const ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD = [
    get('archive-dequeue-book'),
    ...ARCHIVE_WEB_STEPS, 
    buildArchiveUploadStep(false, true), 
    get('archive-report-book-complete')
]

export const GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD = [
    get('git-dequeue-book'),
    ...GIT_WEB_STEPS, 
    get('git-report-book-complete')
]
