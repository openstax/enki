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
