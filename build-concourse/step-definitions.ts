import { Env, IO, RESOURCES } from "./util";

export type Step = {
    name: string
    inputs: string[]
    outputs: string[]
    env: Env
}

export const STEP_MAP = new Map<string, Step>()

function get(stepName: string) {
    const step = STEP_MAP.get(stepName)
    /* istanbul ignore if */
    if (!step) {
        throw new Error(`BUG: Missing step named '${stepName}'`)
    }
    return step
}

function set(step: Step) {
    /* istanbul ignore if */
    if (STEP_MAP.has(step.name)) {
        throw new Error(`BUG: Step already added '${step.name}'`)
    } else {
        STEP_MAP.set(step.name, step)
    }
}

set({name: 'step-fetch', inputs: [IO.BOOK], outputs: [IO.FETCHED], env: {GH_SECRET_CREDS: false, LOCAL_SIDELOAD_REPO_PATH: false}})
set({name: 'step-prebake', inputs: [IO.BOOK, IO.FETCHED], outputs: [IO.FETCH_META, IO.INITIAL_RESOURCES, IO.ASSEMBLED, IO.RESOURCES, IO.ASSEMBLE_META], env: {}})
set({name: 'step-bake', inputs: [IO.BOOK, IO.FETCH_META, IO.ASSEMBLED, IO.RESOURCES], outputs: [IO.BAKED], env: {}})
set({name: 'step-postbake', inputs: [IO.BOOK, IO.FETCHED, IO.ASSEMBLE_META, IO.BAKED], outputs: [IO.BAKE_META, IO.LINKED, IO.SUPER], env: {}})


// GIT_PDF_STEPS
set({name: 'step-pdf', inputs: [IO.BOOK, IO.LINKED, IO.BAKED, IO.FETCHED, IO.RESOURCES], outputs: [IO.ARTIFACTS], env: {}})
set({name: 'step-upload-pdf', inputs: [IO.BOOK, IO.FETCHED, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// GIT_WEB_STEPS
set({name: 'step-bake-web', inputs: [IO.BOOK, IO.FETCH_META, IO.ASSEMBLED, IO.RESOURCES], outputs: [IO.BAKED], env: {}})
set({name: 'step-disassemble', inputs: [IO.BOOK, IO.LINKED, IO.BAKE_META], outputs: [IO.DISASSEMBLE_LINKED], env: {}})
set({name: 'step-jsonify', inputs: [IO.BOOK, IO.FETCH_META, IO.RESOURCES, IO.DISASSEMBLE_LINKED], outputs: [IO.JSONIFIED], env: {}})
set({name: 'step-upload-book', inputs: [IO.BOOK, IO.FETCHED, IO.JSONIFIED, IO.RESOURCES, IO.ANCILLARY], outputs: [IO.ARTIFACTS], env: {CODE_VERSION: true, CORGI_ARTIFACTS_S3_BUCKET: true, PREVIEW_APP_URL_PREFIX: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, CORGI_CLOUDFRONT_URL: false, REX_PROD_PREVIEW_URL: false}})
set({name: 'step-prepare-ancillaries', inputs: [IO.BOOK, IO.FETCH_META, IO.SUPER, IO.RESOURCES], outputs: [IO.ANCILLARY], env: {}})

// GIT_EPUB_STEPS
set({name: 'step-epub', inputs: [IO.BOOK, IO.FETCHED, IO.RESOURCES, IO.DISASSEMBLE_LINKED, IO.BAKED], outputs: [IO.EPUB, IO.ARTIFACTS], env: {}})
set({name: 'step-upload-epub', inputs: [IO.BOOK, IO.FETCHED, IO.ARTIFACTS], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// GIT_GDOC_STEPS
set({name: 'step-docx', inputs: [IO.BOOK, IO.FETCHED, IO.JSONIFIED, IO.DISASSEMBLE_LINKED, IO.RESOURCES], outputs: [IO.DOCX, IO.ARTIFACTS], env: {}})
set({name: 'step-upload-docx', inputs: [IO.BOOK, IO.FETCHED, IO.DOCX], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// PPT_STEPS
set({name: 'step-pptx', inputs: [IO.BOOK, IO.FETCH_META, IO.LINKED, IO.RESOURCES, IO.BAKED], outputs: [IO.PPTX], env: {}})
set({name: 'step-upload-pptx', inputs: [IO.BOOK, IO.FETCHED, IO.PPTX], outputs: [IO.ARTIFACTS], env: {CORGI_ARTIFACTS_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false}})

// Concourse-specific steps
set({name: 'git-dequeue-book', inputs: [RESOURCES.S3_GIT_QUEUE], outputs: [IO.BOOK], env: { S3_QUEUE: RESOURCES.S3_GIT_QUEUE, CODE_VERSION: true, QUEUE_SUFFIX: true }})
set({name: 'git-report-book-complete', inputs: [IO.BOOK], outputs: [], env: {CODE_VERSION: true, WEB_QUEUE_STATE_S3_BUCKET: true, AWS_ACCESS_KEY_ID: true, AWS_SECRET_ACCESS_KEY: true, AWS_SESSION_TOKEN: false, STATE_PREFIX: true}})

export const CLI_GIT_PDF_STEPS = [
    get('step-fetch'),
    get('step-prebake'),
    get('step-bake'),
    get('step-postbake'),
    get('step-pdf'),
]
export const GIT_PDF_STEPS = [
    ...CLI_GIT_PDF_STEPS,
    get('step-upload-pdf'),
]

export const CLI_GIT_WEB_STEPS = [
    get('step-fetch'),
    get('step-prebake'),
    get('step-bake-web'),
    get('step-postbake'),
    get('step-prepare-ancillaries'),
    get('step-disassemble'),
    get('step-jsonify'),
]
export const GIT_WEB_STEPS = [
    ...CLI_GIT_WEB_STEPS,
    get('step-upload-book'),
]

export const CLI_GIT_EPUB_STEPS = [
    get('step-fetch'),
    get('step-prebake'),
    get('step-bake'),
    get('step-postbake'),
    get('step-disassemble'),
    get('step-epub'),
]

export const GIT_EPUB_STEPS = [
    ...CLI_GIT_EPUB_STEPS,
    get('step-upload-epub')
]

export const CLI_GIT_GDOC_STEPS = [
    get('step-fetch'),
    get('step-prebake'),
    get('step-bake'),
    get('step-postbake'),
    get('step-disassemble'),
    get('step-jsonify'),
    get('step-docx'),
]

export const GIT_GDOC_STEPS = [
    ...CLI_GIT_GDOC_STEPS,
    get('step-upload-docx'),
]

export const CLI_GIT_PPTX_STEPS = [
    get('step-fetch'),
    get('step-prebake'),
    get('step-bake'),
    get('step-postbake'),
    get('step-pptx'),
]

export const GIT_PPTX_STEPS = [
    ...CLI_GIT_PPTX_STEPS,
    get('step-upload-pptx')
]

export function buildLookUpBook(inputSource: RESOURCES): Step {
    return {name: 'look-up-book', inputs: [inputSource], outputs: [IO.BOOK, IO.COMMON_LOG], env: { INPUT_SOURCE_DIR: inputSource }}
}

export const GIT_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD = [
    get('git-dequeue-book'),
    ...GIT_WEB_STEPS, 
    get('git-report-book-complete')
]
