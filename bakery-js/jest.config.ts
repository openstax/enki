// Source: https://github.com/apollographql/typescript-repo-template
import type { JestConfigWithTsJest } from 'ts-jest'

const config: JestConfigWithTsJest = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['src'],
  // coverageDirectory: '../coverage',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.test.json' }],
  },
  // testRegex: '/__tests__/.*.test.ts$',
  verbose: true,
  moduleNameMapper: {
    'myjsx/jsx-dev-runtime': '<rootDir>/src/minidom',
  },
}

export default config
