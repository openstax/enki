const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

const taskDir = path.resolve(__dirname, './tasks')
const commandUsage = 'task <taskname> [options]...'

module.exports.command = commandUsage
module.exports.aliases = ['t']
module.exports.describe = 'builds a bakery pipeline task runnable with fly execute'
module.exports.builder = yargs => {
  yargs.usage(`Usage: ${process.env.CALLER || 'build.js'} ${commandUsage}`)
  yargs.positional('taskname', {
    describe: 'name of task to build',
    choices: fs.readdirSync(taskDir).map(file => path.basename(file, '.js')),
    type: 'string'
  }).option('output', {
    alias: ['o'],
    describe: 'path to output file',
    defaultDescription: 'stdout',
    normalize: true,
    requiresArg: true,
    type: 'string'
  }).option('taskargs', {
    alias: ['a'],
    describe: 'args for the task',
    requiresArg: true,
    type: 'string'
  })
}
module.exports.handler = argv => {
  const task = (() => {
    const taskFilePath = path.resolve(taskDir, `${argv.taskname}.js`)
    return require(taskFilePath)
  })()
  const outputFile = argv.output == null
    ? undefined
    : path.resolve(argv.output)
  const taskArgs = argv.taskargs == null
    ? {}
    : yaml.safeLoad(argv.taskargs)

  const taskConfig = task(taskArgs).config

  const forward = fs.readFileSync(path.resolve(__dirname, 'forward.yml'), { encoding: 'utf8' })
  const output = forward + yaml.safeDump(taskConfig)

  if (outputFile) {
    fs.writeFileSync(outputFile, output)
  } else {
    console.log(output)
  }
}
