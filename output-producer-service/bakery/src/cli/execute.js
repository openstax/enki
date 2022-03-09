#!/usr/bin/env node
const path = require('path')
const fs = require('fs')
const http = require('http')
const { execFileSync, spawn } = require('child_process')
const waitPort = require('wait-port')
const which = require('which')
const tmp = require('tmp')
tmp.setGracefulCleanup()

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

const checkDockerMemoryLimit = () => {
  const dockerSettingsPath = path.join(process.env.HOME, 'Library/Group Containers/group.com.docker/settings.json')
  if (fs.existsSync(dockerSettingsPath)) {
    const settings = JSON.parse(fs.readFileSync(dockerSettingsPath))
    if (!(settings.memoryMiB > 4096)) {
      console.warn(`
==============================================
WARNING: Your docker is configured to use less than 4GB of memory.
This causes problems with larger textbooks during the PDF building step.
Consider changing the Docker settings to increase the memory limit
==============================================
`)
    }
  }
}
checkDockerMemoryLimit()

const completion = subprocess => {
  const error = new Error()
  return new Promise((resolve, reject) => {
    subprocess.on('exit', code => {
      if (code === 0) {
        resolve(undefined)
      } else {
        error.message = `Subprocess failed with code ${code}`
        reject(error)
      }
    })
  })
}

const stripLocalPrefix = imageArg => {
  return imageArg.replace(/^(localhost:5000)\//, '')
}

const isArchive = identifier => {
  const re = /col\d{5}/
  return re.test(identifier)
}

const imageDetailsFromArgs = (argv) => {
  let imageDetails = {}
  if (argv.image) {
    imageDetails = extractLocalImageDetails(argv.image)
  }
  if (argv.tag) {
    imageDetails = { tag: argv.tag }
  }
  console.log(`extracted image details: ${JSON.stringify(imageDetails)}`)
  return { image: imageDetails }
}

const extractLocalImageDetails = imageArg => {
  const imageArgStripped = stripLocalPrefix(imageArg)
  const tagNameSeparatorIndex = imageArgStripped.lastIndexOf(':')
  let imageName, imageTag
  if (tagNameSeparatorIndex === -1) {
    imageName = imageArgStripped
  } else {
    imageName = imageArgStripped.slice(0, tagNameSeparatorIndex)
    imageTag = imageArgStripped.slice(tagNameSeparatorIndex + 1)
  }
  const maybeTag = imageTag == null ? {} : { tag: imageTag }
  const details = {
    registry: 'registry:5000',
    name: imageName,
    ...maybeTag
  }
  return details
}

const input = (dataDir, name) => `--input=${name}=${dataDir}/${name}`
const output = (dataDir, name) => {
  const outputDir = path.resolve(dataDir, name)
  if (fs.existsSync(outputDir)) { fs.rmdirSync(outputDir, { recursive: true }) }
  return `--output=${name}=${outputDir}`
}
const COMPOSE_FILE_PATH = path.resolve(__dirname, 'docker-compose.yml')
const BAKERY_PATH = path.resolve(__dirname, '../..')

const flyExecute = async (cmdArgs, { image, persist }) => {
  const children = []

  process.on('exit', code => {
    if (code !== 0) {
      children.forEach(child => {
        if (child.exitCode == null) {
          child.kill('SIGINT')
        }
      })
    }
  })

  const startup = spawn('docker-compose', [
    `--file=${COMPOSE_FILE_PATH}`,
    'up',
    '-d'
  ], {
    stdio: 'inherit'
  })
  children.push(startup)
  await completion(startup)

  let error
  try {
    if (image != null) {
      console.log('waiting for registry to wake up')
      await waitPort({
        protocol: 'http',
        host: 'localhost',
        port: 5000,
        path: '/v2/_catalog',
        timeout: 30000,
        output: 'silent'
      })
      const imageStripped = stripLocalPrefix(image)
      if (imageStripped === image) {
        throw new Error(`Specified image ${image} does not have prefix 'localhost:5000'. Not safe to automatically push!`)
      }
      console.log(`uploading image: ${image}`)
      const pushImage = spawn('docker', [
        'push',
        image
      ], { stdio: 'inherit' })
      await completion(pushImage)
    }

    console.log('waiting for concourse to wake up')
    await waitPort({
      protocol: 'http',
      host: 'localhost',
      port: 8080,
      path: '/api/v1/info',
      timeout: 90000,
      output: 'silent'
    })

    console.log('syncing fly')
    let flyPath
    try {
      flyPath = which.sync('fly')
    } catch {
      console.log('no fly installation detected on PATH')
      const flyDir = path.resolve(process.env.HOME, '.local/bin/')
      flyPath = path.resolve(flyDir, 'bakery-cli-fly')
      fs.mkdirSync(flyDir, { recursive: true })
    }

    let needsDownload = false
    if (fs.existsSync(flyPath)) {
      console.log(`detected fly cli installation at ${flyPath}`)
      const printOldFlyVersion = spawn(flyPath, ['--version'], { stdio: 'inherit' })
      children.push(printOldFlyVersion)
      await completion(printOldFlyVersion)
      try {
        const sync = spawn(flyPath, [
          'sync',
          '-c', 'http://localhost:8080'
        ], { stdio: 'inherit' })
        children.push(sync)
        await completion(sync)
      } catch (err) {
        needsDownload = true
      }
    } else {
      needsDownload = true
    }

    if (needsDownload) {
      console.log('syncing fly cli via direct download')
      const flyUrl = `http://localhost:8080/api/v1/cli?arch=amd64&platform=${process.platform}`
      const newFly = await new Promise((resolve, reject) => {
        let newFlyData = Buffer.from('')
        http.get(flyUrl, response => {
          const { statusCode } = response
          if (statusCode !== 200) { reject(new Error(`Request failed. Code: ${statusCode}`)) }
          response.on('data', chunk => { newFlyData = Buffer.concat([newFlyData, chunk]) })
          response.on('end', () => { resolve(newFlyData) })
        }).on('error', (err) => { reject(new Error(`Connection error. Code: ${err.code || 'undefined'}`)) })
      })
      fs.writeFileSync(flyPath, newFly)
      fs.chmodSync(flyPath, 0o776)
      const printNewFlyVersion = spawn(flyPath, ['--version'], { stdio: 'inherit' })
      children.push(printNewFlyVersion)
      await completion(printNewFlyVersion)
    }

    console.log('logging in')
    const login = spawn(flyPath, [
      'login',
      '-k',
      '-t', 'bakery-cli',
      '-c', 'http://localhost:8080',
      '-u', 'admin',
      '-p', 'admin'
    ], { stdio: 'inherit' })
    children.push(login)
    await completion(login)

    console.log('waiting for concourse to settle')
    await sleep(5000)

    const flyArgs = [
      'execute',
      '-t', 'bakery-cli',
      '--include-ignored',
      ...cmdArgs
    ]
    console.log(`executing fly with args: ${flyArgs}`)
    const execute = spawn(flyPath, flyArgs, {
      stdio: 'inherit',
      env: {
        ...process.env,
        COLUMNS: process.stdout.columns
      }
    })
    children.push(execute)
    await completion(execute)
  } catch (err) {
    if (err.stdout != null) {
      console.log(err.stdout.toString())
    } else {
      console.log(err)
    }
    error = err
  } finally {
    if (!persist) {
      console.log('cleaning up')
      const cleanUp = spawn('docker-compose', [
        `--file=${COMPOSE_FILE_PATH}`,
        'stop'
      ], { stdio: 'inherit' })
      children.push(cleanUp)
      await completion(cleanUp)
    } else {
      console.log('persisting containers')
    }
  }
  if (error != null) {
    throw error
  }
}

const tasks = {
  'fetch-group': (parentCommand) => {
    const commandUsage = 'fetch-group <repo> <slug> <version> <gh-creds>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify({ ...imageDetails, ...{ githubSecretCreds: argv.ghCreds } })}`]
      const taskContent = execFileSync(buildExec, ['task', 'fetch-book-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'repo'), argv.repo)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'version'), argv.version)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        output(dataDir, 'fetched-book-group'),
        output(dataDir, 'resources'),
        output(dataDir, 'unused-resources')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'fg',
      describe: 'fetch a group of books from git',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of the collection to fetch',
          type: 'string'
        }).positional('repo', {
          describe: 'repo of collection to fetch',
          type: 'string'
        }).positional('version', {
          describe: 'version of collection to fetch',
          type: 'string'
        }).positional('gh-creds', {
          describe: 'gh creds to use',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  fetch: (parentCommand) => {
    const commandUsage = 'fetch <server> <collid> <version>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const nebGetFlags = argv.requestLimit == null ? '' : `--request-limit ${argv.requestLimit}`
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify({ ...imageDetails, nebGetFlags: nebGetFlags })}`]
      const taskContent = execFileSync(buildExec, ['task', 'fetch-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'server'), argv.server)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'version'), argv.version)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        output(dataDir, 'fetched-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'f',
      describe: 'fetch a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('server', {
          describe: 'content server to fetch from',
          type: 'string'
        }).positional('collid', {
          describe: 'collection id of collection to fetch',
          type: 'string'
        }).positional('version', {
          describe: 'version of collection to fetch',
          type: 'string'
        }).option('l', {
          alias: 'request-limit',
          describe: 'maximum number of concurrent requests to make',
          type: 'number'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'assemble-group': (parentCommand) => {
    const commandUsage = 'assemble-group <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug
      })}`]
      const taskContent = execFileSync(buildExec, ['task', 'assemble-book-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        input(dataDir, 'fetched-book-group'),
        output(dataDir, 'assembled-book-group')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'ag',
      describe: 'assemble a book group',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  assemble: (parentCommand) => {
    const commandUsage = 'assemble <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'assemble-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'fetched-book'),
        output(dataDir, 'assembled-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'a',
      describe: 'assemble a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'bake-group': (parentCommand) => {
    const commandUsage = 'bake-group <slug> <recipefile> <stylefile>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug
      })}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const styleName = 'stylesheet'
      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'style'), styleName)

      const tmpRecipesDir = tmp.dirSync()
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/recipes/'), { recursive: true })
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/styles/'), { recursive: true })
      fs.copyFileSync(path.resolve(argv.recipefile), path.resolve(tmpRecipesDir.name, `rootfs/recipes/${styleName}.css`))
      fs.copyFileSync(path.resolve(argv.stylefile), path.resolve(tmpRecipesDir.name, `rootfs/styles/${styleName}-pdf.css`))

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'assembled-book-group'),
        `--input=cnx-recipes-output=${tmpRecipesDir.name}`,
        output(dataDir, 'baked-book-group'),
        output(dataDir, 'group-style')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'bg',
      describe: 'bake a book group',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).positional('recipefile', {
          describe: 'path to recipe file',
          type: 'string'
        }).positional('stylefile', {
          describe: 'path to style file',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'bake-kitchen-group': (parentCommand) => {
    const commandUsage = 'bake-kitchen-group <slug> <recipename> <stylefile>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug
      })}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const styleName = argv.recipename
      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'style'), styleName)

      const tmpRecipesDir = tmp.dirSync()
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/styles/'), { recursive: true })
      fs.copyFileSync(path.resolve(argv.stylefile), path.resolve(tmpRecipesDir.name, `rootfs/styles/${styleName}-pdf.css`))

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'assembled-book-group'),
        `--input=cnx-recipes-output=${tmpRecipesDir.name}`,
        output(dataDir, 'baked-book-group'),
        output(dataDir, 'group-style')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'bgk',
      describe: 'bake a book group using kitchen',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).positional('recipename', {
          describe: 'kitchen recipe / book name',
          type: 'string'
        }).positional('stylefile', {
          describe: 'path to style file',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'link-extras': (parentCommand) => {
    const commandUsage = 'link-extras <collid> <server>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify({
          ...imageDetails, ...{ server: argv.server }
        })}`]

      const taskContent = execFileSync(buildExec, ['task', 'link-extras', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'assembled-book'),
        output(dataDir, 'linked-extras')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'l',
      describe: 'amend external book links',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        }).positional('server', {
          describe: 'archive server',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'link-single': (parentCommand) => {
    const commandUsage = 'link-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug,
        server: argv.server
      })}`]

      const taskContent = execFileSync(buildExec, ['task', 'link-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'fetched-book-group'),
        input(dataDir, 'baked-book-group'),
        input(dataDir, 'baked-book-metadata-group'),
        output(dataDir, 'linked-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'ls',
      describe: 'amend external book links',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  bake: (parentCommand) => {
    const commandUsage = 'bake <collid> <recipefile> <stylefile>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const styleName = 'stylesheet'
      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'style'), styleName)

      const tmpRecipesDir = tmp.dirSync()
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/recipes/'), { recursive: true })
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/styles/'), { recursive: true })
      fs.copyFileSync(path.resolve(argv.recipefile), path.resolve(tmpRecipesDir.name, `rootfs/recipes/${styleName}.css`))
      fs.copyFileSync(path.resolve(argv.stylefile), path.resolve(tmpRecipesDir.name, `rootfs/styles/${styleName}-pdf.css`))

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'linked-extras'),
        `--input=cnx-recipes-output=${tmpRecipesDir.name}`,
        output(dataDir, 'baked-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'b',
      describe: 'bake a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        }).positional('recipefile', {
          describe: 'path to recipe file',
          type: 'string'
        }).positional('stylefile', {
          describe: 'path to style file',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'bake-kitchen': (parentCommand) => {
    const commandUsage = 'bake-kitchen <collid> <recipename> <stylefile>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const styleName = argv.recipename
      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'style'), styleName)

      const tmpRecipesDir = tmp.dirSync()
      fs.mkdirSync(path.resolve(tmpRecipesDir.name, 'rootfs/styles/'), { recursive: true })
      fs.copyFileSync(path.resolve(argv.stylefile), path.resolve(tmpRecipesDir.name, `rootfs/styles/${styleName}-pdf.css`))

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'linked-extras'),
        `--input=cnx-recipes-output=${tmpRecipesDir.name}`,
        output(dataDir, 'baked-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'bk',
      describe: 'bake a book using kitchen',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        }).positional('recipename', {
          describe: 'kitchen recipe / book name',
          type: 'string'
        }).positional('stylefile', {
          describe: 'path to style file',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  mathify: (parentCommand) => {
    const commandUsage = 'mathify <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'mathify-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'baked-book'),
        output(dataDir, 'mathified-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'm',
      describe: 'mathify a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'mathify-single': (parentCommand) => {
    const commandUsage = 'mathify-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'mathify-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'group-style'),
        input(dataDir, 'linked-single'),
        output(dataDir, 'mathified-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'ms',
      describe: 'mathify a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'build-pdf': (parentCommand) => {
    const commandUsage = 'build-pdf <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv) || {}
      const taskArgs = [`--taskargs=${JSON.stringify({ ...imageDetails, ...{ bucketName: 'none' } })}`]
      const taskContent = execFileSync(buildExec, ['task', 'build-pdf', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'pdf_filename'), 'collection.pdf')

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'rex-linked'),
        output(dataDir, 'artifacts')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'p',
      describe: 'build a pdf from a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'pdfify-single': (parentCommand) => {
    const commandUsage = 'pdfify-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv) || {}
      const taskArgs = [`--taskargs=${JSON.stringify({ ...imageDetails, ...{ bucketName: 'none' } })}`]
      const taskContent = execFileSync(buildExec, ['task', 'pdfify-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'pdf_filename'), 'collection.pdf')

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'rex-linked'),
        input(dataDir, 'group-style'),
        input(dataDir, 'fetched-book-group'),
        input(dataDir, 'resources'),
        output(dataDir, 'artifacts-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'ps',
      describe: 'build a pdf from a book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'assemble-meta': (parentCommand) => {
    const commandUsage = 'assemble-meta <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'assemble-book-metadata', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'assembled-book'),
        output(dataDir, 'assembled-book-metadata')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'am',
      describe: 'build metadata files from an assembled book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'assemble-meta-group': (parentCommand) => {
    const commandUsage = 'assemble-meta-group <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug
      })}`]
      const taskContent = execFileSync(buildExec, ['task', 'assemble-book-metadata-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        input(dataDir, 'fetched-book-group'),
        input(dataDir, 'assembled-book-group'),
        output(dataDir, 'assembled-book-metadata-group')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'amg',
      describe: 'build metadata files from an assembled book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'bake-meta': (parentCommand) => {
    const commandUsage = 'bake-meta <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book-metadata', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'fetched-book'),
        input(dataDir, 'baked-book'),
        input(dataDir, 'assembled-book-metadata'),
        output(dataDir, 'baked-book-metadata')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'bm',
      describe: 'build metadata files from a baked book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err) })
      }
    }
  },
  'bake-meta-group': (parentCommand) => {
    const commandUsage = 'bake-meta-group <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const singleBookFlag = argv.single
      const taskArgs = [`--taskargs=${JSON.stringify({
        ...imageDetails,
        singleBookFlag: singleBookFlag,
        slug: argv.slug
      })}`]
      const taskContent = execFileSync(buildExec, ['task', 'bake-book-metadata-group', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        input(dataDir, 'fetched-book-group'),
        input(dataDir, 'baked-book-group'),
        input(dataDir, 'assembled-book-metadata-group'),
        output(dataDir, 'baked-book-metadata-group')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'bmg',
      describe: 'build metadata files from a baked book group',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        }).option('s', {
          alias: 'single',
          describe: 'process a single book',
          type: 'boolean',
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err) })
      }
    }
  },
  checksum: (parentCommand) => {
    const commandUsage = 'checksum <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'checksum-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'baked-book'),
        output(dataDir, 'checksum-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'cb',
      describe: 'checksum resources from a baked book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  disassemble: (parentCommand) => {
    const commandUsage = 'disassemble <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'disassemble-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'fetched-book'),
        input(dataDir, 'checksum-book'),
        input(dataDir, 'baked-book-metadata'),
        output(dataDir, 'disassembled-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'd',
      describe: 'disassemble a checksummed book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'disassemble-single': (parentCommand) => {
    const commandUsage = 'disassemble-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'disassemble-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'linked-single'),
        input(dataDir, 'baked-book-metadata-group'),
        output(dataDir, 'disassembled-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'ds',
      describe: 'disassemble a checksummed book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'patch-disassembled-links': (parentCommand) => {
    const commandUsage = 'patch-disassembled-links <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'patch-disassembled-links', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'disassembled-book'),
        output(dataDir, 'disassembled-linked-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'pd',
      describe: 'patch links on a disassembled book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  jsonify: (parentCommand) => {
    const commandUsage = 'jsonify <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'jsonify-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'disassembled-linked-book'),
        output(dataDir, 'jsonified-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'j',
      describe: 'build metadata from disassembled+linked book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'patch-disassembled-links-single': (parentCommand) => {
    const commandUsage = 'patch-disassembled-links-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'patch-disassembled-links-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'disassembled-single'),
        output(dataDir, 'disassembled-linked-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'pds',
      describe: 'patch links on a disassembled book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'jsonify-single': (parentCommand) => {
    const commandUsage = 'jsonify-single <slug>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'jsonify-single', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'slug'), argv.slug)

      const dataDir = path.resolve(argv.data, argv.slug)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'disassembled-linked-single'),
        output(dataDir, 'jsonified-single')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'js',
      describe: 'build metadata from disassembled book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('slug', {
          describe: 'slug of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  linkRex: (parentCommand) => {
    const commandUsage = 'link-rex <identifier>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const archive = isArchive(argv.identifier)
      const inputSrc = archive ? 'mathified-book' : 'mathified-single'
      const contentSrc = archive ? 'archive' : 'git'
      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = [`--taskargs=${JSON.stringify(
        { ...imageDetails, ...{ inputSource: inputSrc, contentSource: contentSrc } }
      )}`]
      const taskContent = execFileSync(buildExec, ['task', 'link-rex', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      const dirname = archive ? 'collection_id' : 'slug'
      fs.writeFileSync(path.resolve(tmpBookDir.name, dirname), argv.identifier)

      const dataDir = path.resolve(argv.data, argv.identifier)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, inputSrc),
        output(dataDir, 'rex-linked')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      describe: 'update external pdf book links to rex',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('identifier', {
          describe: 'collection id of collection to work on (or book slug)',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  gdocify: (parentCommand) => {
    const commandUsage = 'gdocify <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'gdocify-book', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'disassembled-book'),
        output(dataDir, 'gdocified-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      describe: 'modify page XHTML files for gdoc outputs',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'convert-docx': (parentCommand) => {
    const commandUsage = 'convert-docx <collid>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = imageDetails == null
        ? []
        : [`--taskargs=${JSON.stringify(imageDetails)}`]
      const taskContent = execFileSync(buildExec, ['task', 'convert-docx', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, 'gdocified-book'),
        output(dataDir, 'docx-book')
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      describe: 'build docx files from gdocified book',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on',
          type: 'string'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'validate-xhtml': (parentCommand) => {
    const commandUsage = 'validate-xhtml <collid> <inputsource> <inputpath> [validationnames...]'
    const handler = async argv => {
      console.log(argv.validationnames)
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = [`--taskargs=${JSON.stringify(
        { ...imageDetails, ...{ inputSource: argv.inputsource, inputPath: argv.inputpath, contentSource: argv.contentsource, validationNames: argv.validationnames } }
      )}`]
      const taskContent = execFileSync(buildExec, ['task', 'validate-xhtml', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.collid)

      const dataDir = path.resolve(argv.data, argv.collid)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, argv.inputsource)
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'v',
      describe: 'validate XHTML file(s) from a task',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('collid', {
          describe: 'collection id of collection to work on (or book slug)',
          type: 'string'
        }).positional('inputsource', {
          describe: 'input source to consume data from. e.g. baked-book, assembled-book, ...',
          type: 'string'
        }).positional('inputpath', {
          describe: 'path with task outputs for XHTML files to validate',
          type: 'string'
        }).positional('validationnames', {
          describe: 'a list of validations to run on the XHTML files',
          type: 'array'
        }).option('c', {
          alias: 'contentsource',
          describe: 'content source is either "git" or "archive"',
          type: 'string',
          default: 'archive'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  },
  'validate-cnxml': (parentCommand) => {
    const commandUsage = 'validate-cnxml <name> <inputsource> <modulespath> <collectionspath>'
    const handler = async argv => {
      const buildExec = path.resolve(BAKERY_PATH, 'build')

      const imageDetails = imageDetailsFromArgs(argv)
      const taskArgs = [`--taskargs=${JSON.stringify(
        { ...imageDetails, ...{ inputSource: argv.inputsource, modulesPath: argv.modulespath, collectionsPath: argv.collectionspath, contentSource: argv.contentsource } }
      )}`]
      const taskContent = execFileSync(buildExec, ['task', 'validate-cnxml', ...taskArgs])
      const tmpTaskFile = tmp.fileSync()
      fs.writeFileSync(tmpTaskFile.name, taskContent)

      const tmpBookDir = tmp.dirSync()
      fs.writeFileSync(path.resolve(tmpBookDir.name, 'collection_id'), argv.name)

      const dataDir = path.resolve(argv.data, argv.name)

      await flyExecute([
        '-c', tmpTaskFile.name,
        `--input=book=${tmpBookDir.name}`,
        input(dataDir, argv.inputsource)
      ], { image: argv.image, persist: argv.persist })
    }
    return {
      command: commandUsage,
      aliases: 'v',
      describe: 'validate CNXML / collection file(s) from a task',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || `$0 ${parentCommand}`} ${commandUsage}`)
        yargs.positional('name', {
          describe: 'collection id or book slug to work on',
          type: 'string'
        }).positional('inputsource', {
          describe: 'input source to consume data from. e.g. baked-book, assembled-book, ...',
          type: 'string'
        }).positional('modulespath', {
          describe: 'path to module files to validate relative to input (e.g. raw/modules/**.*.cnxml)',
          type: 'string'
        }).positional('collectionspath', {
          describe: 'path to collection files to validate relative to input (e.g. raw/collections/*.xml)',
          type: 'string'
        }).option('c', {
          alias: 'contentsource',
          describe: 'content source is either "git" or "archive"',
          type: 'string',
          default: 'archive'
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  }
}

try {
  const currentVersion = require('../../package.json').version
  const latestVersion = execFileSync('npm', ['show', '@openstax/bakery-cli', 'version']).toString().trim()
  if (currentVersion !== latestVersion) {
    console.error(`\x1b[33mWarning: bakery-cli version is ${currentVersion} - latest is ${latestVersion}\x1b[0m`)
  }
} catch (error) {
  console.error(error)
  console.error('\x1b[33mWarning: could not compare bakery-cli version due to above error\x1b[0m')
}

const yargs = require('yargs')
  .command((() => {
    const commandUsage = 'run'
    return {
      command: commandUsage,
      describe: 'run a bakery task',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || '$0'} ${commandUsage}`)
        return yargs
          .command(tasks.fetch(commandUsage))
          .command(tasks['fetch-group'](commandUsage))
          .command(tasks.assemble(commandUsage))
          .command(tasks['assemble-group'](commandUsage))
          .command(tasks['link-extras'](commandUsage))
          .command(tasks['link-single'](commandUsage))
          .command(tasks.bake(commandUsage))
          .command(tasks['bake-kitchen'](commandUsage))
          .command(tasks['bake-group'](commandUsage))
          .command(tasks['bake-kitchen-group'](commandUsage))
          .command(tasks.mathify(commandUsage))
          .command(tasks['mathify-single'](commandUsage))
          .command(tasks['build-pdf'](commandUsage))
          .command(tasks['pdfify-single'](commandUsage))
          .command(tasks['assemble-meta'](commandUsage))
          .command(tasks['assemble-meta-group'](commandUsage))
          .command(tasks.checksum(commandUsage))
          .command(tasks['bake-meta'](commandUsage))
          .command(tasks['bake-meta-group'](commandUsage))
          .command(tasks.disassemble(commandUsage))
          .command(tasks['disassemble-single'](commandUsage))
          .command(tasks['patch-disassembled-links'](commandUsage))
          .command(tasks['patch-disassembled-links-single'](commandUsage))
          .command(tasks.jsonify(commandUsage))
          .command(tasks['jsonify-single'](commandUsage))
          .command(tasks.linkRex(commandUsage))
          .command(tasks.gdocify(commandUsage))
          .command(tasks['convert-docx'](commandUsage))
          .command(tasks['validate-xhtml'](commandUsage))
          .command(tasks['validate-cnxml'](commandUsage))
          .option('d', {
            alias: 'data',
            demandOption: true,
            describe: 'path to data directory',
            normalize: true,
            type: 'string'
          })
          .option('i', {
            alias: 'image',
            describe: 'name of image to use instead of default',
            type: 'string'
          })
          .option('t', {
            alias: 'tag',
            describe: 'use a particular tag of the default remote task image resource',
            type: 'string'
          })
          .option('p', {
            alias: 'persist',
            describe: 'persist containers after running cli command',
            boolean: true,
            default: false
          })
          .conflicts('i', 't')
      }
    }
  }).call())
  .command((() => {
    const commandUsage = 'up'
    const handler = async _ => {
      const teardown = spawn('docker-compose', [
        `--file=${COMPOSE_FILE_PATH}`,
        'up',
        '-d'
      ], { stdio: 'inherit' })
      await completion(teardown)
    }
    return {
      command: commandUsage,
      describe: 'start up bakery-cli spawned containers',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || '$0'} ${commandUsage}`)
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  }).call())
  .command((() => {
    const commandUsage = 'stop'
    const handler = async argv => {
      const composeCmd = argv.destroy ? 'down' : 'stop'
      const teardown = spawn('docker-compose', [
        `--file=${COMPOSE_FILE_PATH}`,
        composeCmd
      ], { stdio: 'inherit' })
      await completion(teardown)
    }
    return {
      command: commandUsage,
      describe: 'clean up bakery-cli spawned containers',
      builder: yargs => {
        yargs.usage(`Usage: ${process.env.CALLER || '$0'} ${commandUsage}`)
        yargs.option('d', {
          alias: 'destroy',
          describe: 'destroy containers as well',
          boolean: true,
          default: false
        })
      },
      handler: argv => {
        handler(argv).catch((err) => { console.error(err); process.exit(1) })
      }
    }
  }).call())
  .demandCommand(1, 'command required')
  .help()
  .alias('h', 'help')
  .wrap(process.env.COLUMNS)
  .version(false)
  .strict()
  .fail((msg, err, yargs) => {
    if (err) throw err
    console.error(yargs.help())
    console.error(`\nError: ${msg}`)
    process.exit(1)
  })

yargs.argv // eslint-disable-line
