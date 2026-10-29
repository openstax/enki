require('ts-node/register')

const assert = require('node:assert/strict')
const test = require('node:test')
const { normalizeGithubToken } = require('./build-corgi.ts')

test('normalizes Concourse Git credentials', () => {
    assert.equal(normalizeGithubToken('git:github-token:x-oauth-basic'), 'github-token')
})

test('normalizes credentials without Concourse prefixes or suffixes', () => {
    assert.equal(normalizeGithubToken('github-token'), 'github-token')
})

test('normalizes credential prefixes and suffixes independently', () => {
    assert.equal(normalizeGithubToken('git:github-token'), 'github-token')
    assert.equal(normalizeGithubToken('github-token:x-oauth-basic'), 'github-token')
})

const { makePipeline } = require('./build-corgi.ts')
test.before(() => { process.env.CODE_VERSION = 'test-code-version' })

const stagingEnv = () => ({ ...require('./env/corgi-staging.json') })

const corgiSources = (env) => makePipeline(env).resources
    .filter(({ type }) => type === 'corgi-resource')
    .map(({ source }) => source)

test('passes the normalized GitHub token to every corgi resource', () => {
    const env = { ...stagingEnv(), GH_SECRET_CREDS: 'git:((github-api-token))' }
    const sources = corgiSources(env)

    assert.equal(sources.length, 5)
    for (const source of sources) {
        assert.equal(source.github_token, '((github-api-token))')
        assert.equal(source.api_root, env.CORGI_API_URL)
    }
})

test('omits the GitHub token from corgi resources when no credentials are configured', () => {
    const env = stagingEnv()
    delete env.GH_SECRET_CREDS
    const sources = corgiSources(env)

    assert.equal(sources.length, 5)
    for (const source of sources) {
        assert.equal('github_token' in source, false)
    }
})
