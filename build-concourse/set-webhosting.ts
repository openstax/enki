import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import { execSync } from 'child_process';
import * as yaml from 'js-yaml';

const getEnv = (key: string, fallback?: string): string => {
  const value = process.env[key];
  if (value === undefined || value.length === 0) {
    if (fallback === undefined) {
      throw new Error(`Missing environment variable: ${key}`)
    }
    return fallback;
  }
  return value;
}

const CODE_VERSION = getEnv('CODE_VERSION');
const WEBHOST_YAML = getEnv('WEBHOST_YML', './webhosting-production.yml');
const WEBHOST_PREFIX = getEnv('WEBHOST_PREFIX', 'webhost-prod-');
const HUB_API_URL = getEnv('DOCKER_HUB_API', 'https://hub.docker.com/v2');

// Fetch functions stolen from CORGI
const _hadUnexpectedError = (response: { status: number }) =>
  !(response.status >= 200 && response.status < 400);

const _hadAuthError = (response: { status: number }) =>
  response.status === 401 || response.status === 403;

const _handleFetchError = async (response: Response) => {
  if (_hadAuthError(response)) {
    throw new Error('Authentication required');
  } else if (_hadUnexpectedError(response)) {
    if (response.headers.get('content-type') === 'application/json') {
      let error: string;
      try {
        error = await response.text();
      } catch {
        error = "An unknown error occurred";
      }
      throw new Error(error);
    } else {
      throw new Error(`${response.status}: "${response.statusText}"`);
    }
  }
  return response;
}

class DockerHubAPI {
  constructor(public readonly apiUrl: string) { }

  protected async fetch(
    input: URL | RequestInfo,
    init?: RequestInit | undefined,
  ) {
    return await _handleFetchError(await fetch(input as any, init as any));
  }

  protected async fetchJSON(
    input: URL | RequestInfo,
    init?: RequestInit | undefined,
  ) {
    return await (await this.fetch(input, init)).json();
  }

  protected buildUrl(...args: string[]) {
    return `${this.apiUrl}/${args.join('/')}`;
  }

  // https://docs.docker.com/docker-hub/api/latest/#tag/repositories
  protected buildRepoUrl(owner: string, repository: string, ...rest: string[]) {
    return this.buildUrl(
      'namespaces',
      owner,
      'repositories',
      repository,
      ...rest,
    );
  }

  async getTag(owner: string, repository: string, tag: string) {
    const tagsUrl = this.buildRepoUrl(owner, repository, 'tags', tag);
    const tagJson = await this.fetchJSON(tagsUrl);
    // This should never happen, just being extra cautious
    if ((tagJson.digest ?? '').trim().length === 0) {
      throw new Error(`Failed to fetch "${tag}"`);
    }
    return tagJson;
  }
}

const getFlyTarget = () => {
  const flyrcPath = path.resolve(os.homedir(), '.flyrc');
  const flyrc: any = yaml.load(fs.readFileSync(flyrcPath, 'utf-8'));
  const targets = flyrc.targets;
  for (const targetName of Object.keys(targets)) {
    const value = targets[targetName];
    if (value.api.match(/\.openstax\.org\/?$/)) {
      return targetName;
    }
  }
  throw new Error('Could not find fly target');
}

const getCommand = (command: string) => {
  return (args: string, options = {}) => {
    try {
      return execSync(`${command} ${args}`, options)?.toString('utf-8');
    } catch (e) {
      throw new Error(`Exit ${e.status}: ${e.stderr?.toString('utf-8')}`);
    }
  };
}

const getFlyCommand = (flyTarget: string) => {
  const fly = getCommand('fly');
  const interactive = { stdio: [0, 0, 0] }
  return (args: string, opts = interactive) =>
    fly(`-t ${flyTarget} ${args}`, opts);
}

const main = async () => {
  const dockerHub = new DockerHubAPI(HUB_API_URL);
  const fly = getFlyCommand(getFlyTarget());
  const imageDigest =
    (await dockerHub.getTag('openstax', 'enki', CODE_VERSION)).digest;
  console.log(`Code version "${CODE_VERSION}" found! (${imageDigest})`);
  fly(`sp -p ${WEBHOST_PREFIX}${CODE_VERSION} -c ${WEBHOST_YAML}`);
}

main().catch((err) => { throw err })
