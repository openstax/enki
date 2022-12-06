// Source: https://github.com/apollographql/typescript-repo-template
import type { Config } from '@jest/types';

const config: Config.InitialOptions = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['src'],
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.test.json',
    },
  },
  // testRegex: '/__tests__/.*.test.ts$',
  verbose: true,
  moduleNameMapper: {
    'myjsx/jsx-dev-runtime': '<rootDir>/src/minidom'
  }
};

export default config;