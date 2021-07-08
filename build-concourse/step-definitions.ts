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

const STEP_MAP = new Map<string, Step>()

function get(stepName: string) {
    if (!STEP_MAP.has(stepName)) {
        throw new Error(`BUG: Missing step named '${stepName}'`)
    }
    return STEP_MAP.get(stepName)
}

// ARCHIVE_WEB_STEPS
STEP_MAP.set('archive-fetch', {name: 'archive-fetch', inputs: [IO.BOOK], outputs: [IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-fetch-metadata', {name: 'archive-fetch-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-validate-cnxml', {name: 'archive-validate-cnxml', inputs: [IO.ARCHIVE_FETCHED], outputs: [], env: {}})
STEP_MAP.set('archive-assemble', {name: 'archive-assemble', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-assemble-metadata', {name: 'archive-assemble-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-link-extras', {name: 'archive-link-extras', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-bake', {name: 'archive-bake', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-bake-metadata', {name: 'archive-bake-metadata', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-validate-xhtml-baked', {name: 'archive-validate-xhtml-baked', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.BOOK, IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-checksum', {name: 'archive-checksum', inputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], env: {}})
STEP_MAP.set('archive-disassemble', {name: 'archive-disassemble', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-patch-disassembled-links', {name: 'archive-patch-disassembled-links', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-jsonify', {name: 'archive-jsonify', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_JSONIFIED, IO.ARTIFACTS], env: {}})
STEP_MAP.set('archive-validate-xhtml-jsonify', {name: 'archive-validate-xhtml-jsonify', inputs: [IO.BOOK, IO.ARCHIVE_JSONIFIED], outputs: [IO.BOOK, IO.ARCHIVE_BOOK], env: {}})

// GIT_PDF_STEPS
STEP_MAP.set('git-fetch', {name: 'git-fetch', inputs: [IO.BOOK], outputs: [IO.FETCHED], env: {GH_SECRET_CREDS: false}})
STEP_MAP.set('git-fetch-metadata', {name: 'git-fetch-metadata', inputs: [IO.BOOK, IO.FETCHED], outputs: [IO.FETCH_META, IO.RESOURCES, IO.UNUSED_RESOURCES], env: {}})
STEP_MAP.set('git-validate-cnxml', {name: 'git-validate-cnxml', inputs: [IO.FETCHED], outputs: [], env: {}})
STEP_MAP.set('git-assemble', {name: 'git-assemble', inputs: [IO.BOOK, IO.FETCH_META], outputs: [IO.ASSEMBLED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-assemble-meta', {name: 'git-assemble-meta', inputs: [IO.BOOK, IO.ASSEMBLED], outputs: [IO.ASSEMBLE_META], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-bake', {name: 'git-bake', inputs: [IO.BOOK, IO.ASSEMBLED], outputs: [IO.BAKED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-bake-meta', {name: 'git-bake-meta', inputs: [IO.BOOK, IO.ASSEMBLE_META, IO.BAKED], outputs: [IO.BAKE_META], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-validate-xhtml-baked', {name: 'git-validate-xhtml-baked', inputs: [IO.BAKED], outputs: [], env: {}})
STEP_MAP.set('git-link', {name: 'git-link', inputs: [IO.BOOK, IO.BAKED, IO.BAKE_META], outputs: [IO.LINKED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-mathify', {name: 'git-mathify', inputs: [IO.BOOK, IO.LINKED, IO.BAKED], outputs: [IO.MATHIFIED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-pdfify', {name: 'git-pdfify', inputs: [IO.BOOK, IO.MATHIFIED], outputs: [IO.ARTIFACTS], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-pdfify-meta', {name: 'git-pdfify-meta', inputs: [IO.BOOK, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true}})

// GIT_WEB_STEPS
STEP_MAP.set('git-disassemble', {name: 'git-disassemble', inputs: [IO.BOOK, IO.LINKED, IO.BAKE_META], outputs: [IO.DISASSEMBLED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-patch-disassembled-links', {name: 'git-patch-disassembled-links', inputs: [IO.BOOK, IO.DISASSEMBLED], outputs: [IO.DISASSEMBLE_LINKED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-jsonify', {name: 'git-jsonify', inputs: [IO.BOOK, IO.DISASSEMBLE_LINKED], outputs: [IO.JSONIFIED], env: {ARG_OPT_ONLY_ONE_BOOK: false}})
STEP_MAP.set('git-validate-xhtml-jsonify', {name: 'git-validate-xhtml-jsonify', inputs: [IO.BOOK, IO.JSONIFIED], outputs: [], env: {}})
STEP_MAP.set('git-upload-book', {name: 'git-upload-book', inputs: [IO.BOOK, IO.JSONIFIED, IO.RESOURCES], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// ARCHIVE_PDF_STEPS
STEP_MAP.set('archive-mathify', {name: 'archive-mathify', inputs: [IO.BOOK, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK], env: {}})
STEP_MAP.set('archive-pdf', {name: 'archive-pdf', inputs: [IO.BOOK, IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARTIFACTS], env: {}})
STEP_MAP.set('archive-pdf-metadata', {name: 'archive-pdf-metadata', inputs: [IO.BOOK, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true}})

// ARCHIVE_GDOC_STEPS
STEP_MAP.set('archive-gdocify', {name: 'archive-gdocify', inputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED], outputs: [IO.ARCHIVE_GDOCIFIED], env: {}})
STEP_MAP.set('archive-convert-docx', {name: 'archive-convert-docx', inputs: [IO.ARCHIVE_GDOCIFIED], outputs: [IO.ARCHIVE_GDOCIFIED], env: {}})
STEP_MAP.set('archive-upload-docx', {name: 'archive-upload-docx', inputs: [IO.BOOK, IO.ARCHIVE_GDOCIFIED], outputs: [IO.ARCHIVE_GDOCIFIED], env: {GOOGLE_SERVICE_ACCOUNT_CREDENTIALS: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// Concourse-specific steps
STEP_MAP.set('archive-dequeue-book', {name: 'archive-dequeue-book', inputs: [RESOURCES.S3_QUEUE], outputs: [IO.BOOK], env: { S3_QUEUE: RESOURCES.S3_QUEUE, CODE_VERSION: true }})
STEP_MAP.set('archive-report-book-complete', {name: 'archive-report-book-complete', inputs: [IO.BOOK], outputs: [], env: {CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// STEP_MAP.set('archive-upload-book', {name: 'archive-upload-book', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_JSONIFIED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_UPLOAD], env: {CORGI_ARTIFACTS_S3_BUCKET: requireCorgiBucket, WEB_S3_BUCKET: requireWebhostingBucket, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})
// STEP_MAP.set('git-look-up-book', {name: 'git-look-up-book', inputs: [inputSource], outputs: [IO.BOOK, IO.COMMON_LOG], env: { INPUT_SOURCE_DIR: inputSource }})
// STEP_MAP.set('archive-look-up-book', {name: 'archive-look-up-book', inputs: [inputSource], outputs: [IO.BOOK, IO.COMMON_LOG], env: { INPUT_SOURCE_DIR: inputSource }})


// These are used both by CORGI when building a preview and by the webhosting pipeline
const ARCHIVE_WEB_STEPS: Step[] = [
    get('archive-fetch'),
    get('archive-fetch-metadata'),
    // get('archive-validate-cnxml'),
    get('archive-assemble'),
    get('archive-assemble-metadata'),
    get('archive-link-extras'),
    get('archive-bake'),
    get('archive-validate-xhtml-baked'),
    get('archive-bake-metadata'),
    get('archive-checksum'),
    get('archive-disassemble'),
    get('archive-patch-disassembled-links'),
    get('archive-jsonify'),
    get('archive-validate-xhtml-jsonify'),
]

export const GIT_PDF_STEPS: Step[] = [
    get('git-fetch'),
    get('git-fetch-metadata'),
    // get('git-validate-cnxml'),
    get('git-assemble'),
    get('git-assemble-meta'),
    get('git-bake'),
    get('git-validate-xhtml-baked'),
    get('git-bake-meta'),
    get('git-link'),
    get('git-mathify'),
    get('git-pdfify'),
    get('git-pdfify-meta'),
]

export const GIT_WEB_STEPS: Step[] = [
    get('git-fetch'),
    get('git-fetch-metadata'),
    // get('git-validate-cnxml'),
    get('git-assemble'),
    get('git-assemble-meta'),
    get('git-bake'),
    get('git-validate-xhtml-baked'),
    get('git-bake-meta'),
    get('git-link'),
    get('git-disassemble'),
    get('git-patch-disassembled-links'),
    get('git-jsonify'),
    get('git-validate-xhtml-jsonify'),
    get('git-upload-book'),
]


export const ARCHIVE_PDF_STEPS: Step[] = [
    get('archive-fetch'),
    // get('archive-validate-cnxml'),
    get('archive-assemble'),
    get('archive-link-extras'),
    get('archive-bake'),
    get('archive-validate-xhtml-baked'),
    get('archive-mathify'),
    get('archive-pdf'),
    get('archive-pdf-metadata'),
]


export const ARCHIVE_GDOC_STEPS = [
    ...ARCHIVE_WEB_STEPS, // up to archive-validate-xhtml
    get('archive-gdocify'),
    get('archive-convert-docx'),
    get('archive-upload-docx'),
]

function buildUploadStep(requireCorgiBucket: boolean, requireWebhostingBucket: boolean) {
    return {name: 'archive-upload-book', inputs: [IO.BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_JSONIFIED, IO.ARCHIVE_BOOK], outputs: [IO.ARCHIVE_BOOK, IO.ARCHIVE_FETCHED, IO.ARCHIVE_UPLOAD], env: {CORGI_ARTIFACTS_S3_BUCKET: requireCorgiBucket, WEB_S3_BUCKET: requireWebhostingBucket, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}}
}

export function buildLookUpBook(gitOrArchive: GIT_OR_ARCHIVE, inputSource: RESOURCES): Step {
    return {name: gitOrArchive == GIT_OR_ARCHIVE.GIT ? 'git-look-up-book' : 'archive-look-up-book', inputs: [inputSource], outputs: [IO.BOOK, IO.COMMON_LOG], env: { INPUT_SOURCE_DIR: inputSource }}
}

export const ARCHIVE_WEB_STEPS_WITH_UPLOAD = [...ARCHIVE_WEB_STEPS, buildUploadStep(true, false)]

export const ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD = [
    get('archive-dequeue-book'),
    ...ARCHIVE_WEB_STEPS, 
    buildUploadStep(false, true), 
    get('archive-report-book-complete')
]
