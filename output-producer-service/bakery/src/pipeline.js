const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

const pipelineDir = path.resolve(__dirname, './pipelines')
const envDir = path.resolve(__dirname, '../env')
const commandUsage = 'pipeline <pipelinetype> <env> [options]...'

module.exports.command = commandUsage
module.exports.aliases = ['p']
module.exports.describe = 'builds a pipeline runnable with fly command'
module.exports.builder = yargs => {
  yargs.usage(`Usage: ${process.env.CALLER || 'build.js'} ${commandUsage}`)
  yargs.positional('pipelinetype', {
    describe: 'type of pipeline',
    choices: fs.readdirSync(pipelineDir).map(file => path.basename(file, '.js')),
    type: 'string'
  }).positional('env', {
    describe: 'name of environment',
    choices: fs.readdirSync(envDir).map(file => path.basename(file, '.json')),
    type: 'string'
  }).option('output', {
    alias: ['o'],
    describe: 'path to output file',
    defaultDescription: 'stdout',
    normalize: true,
    requiresArg: true,
    type: 'string'
  }).option('tag', {
    alias: ['t'],
    describe: 'pin pipeline image resources to a tag in the config',
    type: 'string'
  })
}
module.exports.handler = argv => {
  const env = (() => {
    const envFilePath = path.resolve(envDir, `${argv.env}.json`)
    try {
      return require(envFilePath)
    } catch {
      throw new Error(`Could not find environment file: ${envFilePath}`)
    }
  }).call()
  const s3Keys = (() => {
    // Grab AWS and GH credentials from environment when running locally. If not
    // available, throw an explicit error for the user
    // GH credentials are in the form `username:personal-access-token`
    if (env.ENV_NAME === 'local') {
      const localAKI = process.env.AWS_ACCESS_KEY_ID
      const localSAK = process.env.AWS_SECRET_ACCESS_KEY
      const localGithubCreds = process.env.GH_SECRET_CREDS
      if (localAKI === undefined) {
        throw new Error('Please set AWS_ACCESS_KEY_ID in your environment')
      }
      if (localSAK === undefined) {
        throw new Error('Please set AWS_SECRET_ACCESS_KEY in your environment')
      }
      if (localGithubCreds === undefined) {
        throw new Error('Please set GH_SECRET_CREDS in your environment')
      }
      return {
        S3_ACCESS_KEY_ID: localAKI,
        S3_SECRET_ACCESS_KEY: localSAK,
        GH_SECRET_CREDS: localGithubCreds
      }
    }
    if (argv.pipelinetype === 'cops') {
      return {
        S3_ACCESS_KEY_ID: env.COPS_BUCKET_AKI_SECRET_NAME,
        S3_SECRET_ACCESS_KEY: env.COPS_BUCKET_SAK_SECRET_NAME,
        GH_SECRET_CREDS: env.GH_SECRET_CREDS
      }
    }
    if (['distribution', 'gdoc', 'git-distribution'].includes(argv.pipelinetype)) {
      return {
        S3_ACCESS_KEY_ID: env.WEB_BUCKET_AKI_SECRET_NAME,
        S3_SECRET_ACCESS_KEY: env.WEB_BUCKET_SAK_SECRET_NAME,
        GH_SECRET_CREDS: env.GH_SECRET_CREDS
      }
    }
    return {
      S3_ACCESS_KEY_ID: 'no-secret-resolved',
      S3_SECRET_ACCESS_KEY: 'no-secret-resolved',
      GH_SECRET_CREDS: 'no-secret-resolved'
    }
  }).call()
  const dockerCredentials = (() => {
    let dockerUsername
    let dockerPassword

    if (env.ENV_NAME === 'local') {
      dockerUsername = process.env.DOCKERHUB_USERNAME
      dockerPassword = process.env.DOCKERHUB_PASSWORD
    } else {
      dockerUsername = env.DOCKERHUB_USERNAME
      dockerPassword = env.DOCKERHUB_PASSWORD
    }
    if ((dockerUsername != null) && (dockerPassword != null)) {
      return {
        dockerCredentials: {
          username: dockerUsername,
          password: dockerPassword
        }
      }
    } else {
      return {}
    }
  }).call()
  const pipeline = (() => {
    const pipelineFilePath = path.resolve(pipelineDir, `${argv.pipelinetype}.js`)
    return require(pipelineFilePath)
  }).call()
  const outputFile = argv.output == null
    ? undefined
    : path.resolve(argv.output)

  const pipelineArgs = { ...env, ...s3Keys, ...dockerCredentials, ...(argv.tag == null ? {} : { IMAGE_TAG: argv.tag }) }
  const pipelineConfig = pipeline(pipelineArgs).config

  const forward = fs.readFileSync(path.resolve(__dirname, 'forward.yml'), { encoding: 'utf8' })
  let output
  try {
    output = forward + yaml.safeDump(pipelineConfig)
  } catch (err) {
    console.error(yaml.dump(pipelineConfig))
    console.error('An error occurred during safeDump. ^^ A dump without safety is above ^^ grep on stderr might help?')
    throw err
  }

  if (outputFile) {
    fs.writeFileSync(outputFile, output)
  } else {
    console.log(output)
  }
}
