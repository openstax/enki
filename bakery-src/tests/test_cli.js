const test = require('ava')
const { spawn } = require('child_process')
const fs = require('fs-extra')
const path = require('path')
const yaml = require('js-yaml')
const dedent = require('dedent')

const completion = subprocess => {
  const error = new Error()
  return new Promise((resolve, reject) => {
    let stdout = ''
    let stderr = ''
    subprocess.stdout.on('data', data => {
      stdout += data.toString()
    })
    subprocess.stderr.on('data', data => {
      stderr += data.toString()
    })
    subprocess.on('error', err => {
      reject(err)
    })
    subprocess.on('close', (code, signal) => {
      if (code === 0) {
        resolve({ stdout, stderr })
      } else {
        error.message = `Subprocess failed with code ${code}, signal ${signal}, and captured output: \n${formatSubprocessOutput({ stdout, stderr })}`
        reject(error)
      }
    })
  })
}

const formatSubprocessOutput = (result) => {
  return dedent`
  ###### stdout ######
  ${result.stdout}
  ###### stderr ######
  ${result.stderr}
  `
}

const sourceObjs = (obj) => {
  const sources = []
  if (typeof obj !== 'object') { return sources }
  if (obj instanceof Array) {
    for (const subobj of obj) {
      sources.push(...sourceObjs(subobj))
    }
  }
  if (obj.type != null && obj.type === 'docker-image') {
    sources.push(obj.source)
  } else {
    for (const key of Object.keys(obj)) {
      if (obj[key] == null) {
        throw new Error(`${key} is null`)
      }
      sources.push(...sourceObjs(obj[key]))
    }
  }
  return sources
}

const allParam = (obj, param) => {
  const values = []
  if (typeof obj !== 'object') { return values }
  if (obj instanceof Array) {
    for (const subobj of obj) {
      values.push(...allParam(subobj, param))
    }
  }
  if (obj[param] != null) {
    values.push(obj[param])
  } else {
    for (const key of Object.keys(obj)) {
      values.push(...allParam(obj[key], param))
    }
  }
  return values
}

test('build pipelines', async t => {
  const envs = (await fs.readdir('env')).map(file => path.basename(file, '.json'))
  const pipelines = (await fs.readdir('src/pipelines')).map(file => path.basename(file, '.js'))

  const processes = []
  for (const pipeline of pipelines) {
    for (const env of envs) {
      processes.push(
        completion(spawn('./build', [
          'pipeline',
          pipeline,
          env
        ],
        {
          // Include credentials in environment for local pipelines
          env: {
            ...process.env,
            ...{
              AWS_ACCESS_KEY_ID: 'accesskey',
              AWS_SECRET_ACCESS_KEY: 'secret',
              GH_SECRET_CREDS: 'username:secret'
            }
          }
        }
        ))
      )
    }
  }

  await Promise.all(processes)
  t.pass()
})

test('non-local pipelines do not use credentials in env vars', async t => {
  const pipelines = (await fs.readdir('src/pipelines')).map(file => path.basename(file, '.js'))

  for (const pipeline of pipelines) {
    for (const env of ['staging', 'prod']) {
      const fakeAKI = 'testaccesskeyidtest'
      const fakeSAK = 'testsecretaccesskeytest'
      const fakeGHCreds = 'username:secret'
      const fakeDHU = 'testdockerhubuser'
      const fakeDHP = 'testdockerhubpassword'
      const result = await completion(spawn('./build', [
        'pipeline',
        pipeline,
        env
      ],
      {
        // Pretend environment variables are set
        env: {
          ...process.env,
          ...{
            AWS_ACCESS_KEY_ID: fakeAKI,
            AWS_SECRET_ACCESS_KEY: fakeSAK,
            GH_SECRET_CREDS: fakeGHCreds,
            DOCKERHUB_USERNAME: fakeDHU,
            DOCKERHUB_PASSWORD: fakeDHP
          }
        }
      }
      ))
      t.false(result.stdout.includes(fakeAKI))
      t.false(result.stderr.includes(fakeAKI))
      t.false(result.stdout.includes(fakeSAK))
      t.false(result.stderr.includes(fakeSAK))
      t.false(result.stdout.includes(fakeGHCreds))
      t.false(result.stderr.includes(fakeGHCreds))
      t.false(result.stdout.includes(fakeDHU))
      t.false(result.stderr.includes(fakeDHU))
      t.false(result.stdout.includes(fakeDHP))
      t.false(result.stderr.includes(fakeDHP))
    }
  }
})

test('local pipelines error without credentials', async t => {
  const pipelines = (await fs.readdir('src/pipelines')).map(file => path.basename(file, '.js'))

  for (const pipeline of pipelines) {
    const subproc = async () => {
      await completion(spawn('./build', [
        'pipeline',
        pipeline,
        'local'
      ]))
    }

    await t.throwsAsync(
      subproc,
      { message: /Please set AWS_ACCESS_KEY_ID in your environment/ }
    )
  }
})

test('staging and prod secret names differ', async t => {
  for (const pipeline of ['distribution', 'gdoc']) {
    let stagingOut = ''
    const stagingPipeline = spawn('./build', [
      'pipeline',
      pipeline,
      'staging'
    ])
    stagingPipeline.stdout.on('data', (data) => {
      stagingOut += data.toString()
    })
    await completion(stagingPipeline)
    const stagingOutObj = yaml.safeLoad(stagingOut)
    const stagingAkiSet = new Set(allParam(stagingOutObj, 'AWS_ACCESS_KEY_ID'))
    const stagingSakSet = new Set(allParam(stagingOutObj, 'AWS_SECRET_ACCESS_KEY'))
    t.is(stagingAkiSet.size, 1, pipeline + ' staging: ' + JSON.stringify([...stagingAkiSet]))
    t.is(stagingSakSet.size, 1, pipeline + ' staging: ' + JSON.stringify([...stagingSakSet]))

    let prodOut = ''
    const prodPipeline = spawn('./build', [
      'pipeline',
      pipeline,
      'prod'
    ])
    prodPipeline.stdout.on('data', (data) => {
      prodOut += data.toString()
    })
    await completion(prodPipeline)
    const prodOutObj = yaml.safeLoad(prodOut)
    const prodAkiSet = new Set(allParam(prodOutObj, 'AWS_ACCESS_KEY_ID'))
    const prodSakSet = new Set(allParam(prodOutObj, 'AWS_SECRET_ACCESS_KEY'))
    t.is(prodAkiSet.size, 1, pipeline + ' prod: ' + JSON.stringify([...prodAkiSet]))
    t.is(prodSakSet.size, 1, pipeline + ' prod: ' + JSON.stringify([...prodSakSet]))

    t.not([...stagingAkiSet][0], [...prodAkiSet][0])
    t.not([...stagingSakSet][0], [...prodSakSet][0])
  }
})

test('credentials for local pipelines', async t => {
  const fakeAKI = 'testaccesskeyidtest'
  const fakeSAK = 'testsecretaccesskeytest'
  const fakeGHCreds = 'username:secret'
  const fakeDHU = 'testdockerhubuser'
  const fakeDHP = 'testdockerhubpassword'
  const fakeCreds = {
    AWS_ACCESS_KEY_ID: fakeAKI,
    AWS_SECRET_ACCESS_KEY: fakeSAK,
    GH_SECRET_CREDS: fakeGHCreds,
    DOCKERHUB_USERNAME: fakeDHU,
    DOCKERHUB_PASSWORD: fakeDHP

  }

  for (const pipeline of ['distribution', 'gdoc']) {
    const result = await completion(spawn('./build', [
      'pipeline',
      pipeline,
      'local'
    ],
    {
      // Pretend environment variables are set
      env: {
        ...process.env,
        ...fakeCreds
      }
    }
    ))
    t.true(result.stdout.includes(fakeAKI))
    t.true(result.stdout.includes(fakeSAK))
    t.true(result.stdout.includes(fakeDHU))
    t.true(result.stdout.includes(fakeDHP))
  }

  for (const pipeline of ['cops']) {
    const result = await completion(spawn('./build', [
      'pipeline',
      pipeline,
      'local'
    ],
    {
      // Pretend environment variables are set
      env: {
        ...process.env,
        ...fakeCreds
      }
    }
    ))
    t.true(result.stdout.includes(fakeAKI))
    t.true(result.stdout.includes(fakeSAK))
    t.true(result.stdout.includes(fakeGHCreds))
    t.true(result.stdout.includes(fakeDHU))
    t.true(result.stdout.includes(fakeDHP))
  }
})

test('default tag is trunk', async t => {
  let pipelineOut = ''
  const buildPipeline = spawn('./build', [
    'pipeline',
    'cops',
    'prod'
  ])
  buildPipeline.stdout.on('data', (data) => {
    pipelineOut += data.toString()
  })
  const buildPipelineResult = await completion(buildPipeline)

  const obj = yaml.safeLoad(pipelineOut)
  const sources = sourceObjs(obj)
  for (const source of sources) {
    t.is(source.tag, 'trunk', formatSubprocessOutput(buildPipelineResult))
  }
})

test('pin pipeline tasks to versions', async t => {
  const customTag = 'my-custom-tag'
  let pipelineOut = ''
  const buildPipeline = spawn('./build', [
    'pipeline',
    'cops',
    'prod',
    `--tag=${customTag}`
  ])
  buildPipeline.stdout.on('data', (data) => {
    pipelineOut += data.toString()
  })
  const buildPipelineResult = await completion(buildPipeline)

  const obj = yaml.safeLoad(pipelineOut)
  const sources = sourceObjs(obj)
  for (const source of sources) {
    t.is(source.tag, customTag, formatSubprocessOutput(buildPipelineResult))
  }
})

const startHeartBeat = () => {
  // Log a heartbeat every minute so CI doesn't timeout
  setInterval(() => {
    console.log('HEARTBEAT\n   /\\ \n__/  \\  _ \n      \\/')
  }, 60000)
}

const wipeSlateClean = async (outputDir, dataDir, bookId) => {
  try {
    await fs.rmdir(outputDir, { recursive: true })
  } catch { }
  await fs.copy(`${dataDir}/${bookId}`, `${outputDir}/${bookId}`)
}

test('stable flow pipelines', async t => {
  // Prepare Test Data for Archive Pipelines
  const dataDir = 'src/tests/data'
  const bookId = 'col30149'
  const outputDir = 'src/tests/output'
  wipeSlateClean(outputDir, dataDir, bookId)

  // Prepare test data for Git Piplines
  const bookSlug = 'business-law-i-essentials'
  const gitOutputDir = 'src/tests/output-git'
  wipeSlateClean(gitOutputDir, dataDir, bookSlug)

  // Build Local cops-bakery-scripts Image
  const scriptsImageBuild = spawn('docker', [
    'build',
    'src/scripts',
    '--tag=localhost:5000/openstax/cops-bakery-scripts:test'
  ])
  await completion(scriptsImageBuild)

  startHeartBeat()

  // Start Running (Joint) Archive Pipeline Tasks
  const commonArgs = [
    'run',
    `--data=${outputDir}`,
    '--persist'
  ]

  const validateCnxml = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'validate-cnxml',
    bookId,
    'fetched-book',
    'raw/**/index.cnxml',
    'raw/collection.xml'
  ])

  await completion(validateCnxml)

  const assemble = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'assemble',
    bookId
  ])
  const assembleResult = await completion(assemble)
  const outputAssemble = `${outputDir}/${bookId}/assembled-book/${bookId}/collection.assembled.xhtml`
  t.truthy(fs.existsSync(outputAssemble), formatSubprocessOutput(assembleResult))

  const assembleValidateXhtml = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'validate-xhtml',
    bookId,
    'assembled-book',
    'collection.assembled.xhtml',
    'link-to-duplicate-id'
  ])
  await completion(assembleValidateXhtml)

  const assembleMeta = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'assemble-meta',
    bookId
  ])
  const assembleMetaResult = await completion(assembleMeta)
  const outputAssembleMeta = `${outputDir}/${bookId}/assembled-book-metadata/${bookId}/collection.assembled-metadata.json`
  t.truthy(fs.existsSync(outputAssembleMeta), formatSubprocessOutput(assembleMetaResult))

  const linkExtras = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'link-extras',
    bookId,
    'dummy-archive'
  ])
  const linkResult = await completion(linkExtras)
  const outputLinkExtras = `${outputDir}/${bookId}/linked-extras/${bookId}/collection.linked.xhtml`
  t.truthy(fs.existsSync(outputLinkExtras), formatSubprocessOutput(linkResult))

  const bake = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'bake',
    bookId,
    `${dataDir}/col30149-recipe.css`,
    `${dataDir}/blank-style.css`
  ])
  const bakeResult = await completion(bake)
  const outputBake = `${outputDir}/${bookId}/baked-book/${bookId}/collection.baked.xhtml`
  t.truthy(fs.existsSync(outputBake), formatSubprocessOutput(bakeResult))

  const bakeValidateXhtml = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'validate-xhtml',
    bookId,
    'baked-book',
    'collection.baked.xhtml',
    'link-to-duplicate-id'
  ])
  await completion(bakeValidateXhtml)

  // Continue Archive PDF Pipeline
  const mathify = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    'mathify',
    bookId
  ])
  const branchArchivePDF = completion(mathify).then(async (mathifyResult) => {
    const outputMathified = `${outputDir}/${bookId}/mathified-book/${bookId}/collection.mathified.xhtml`
    t.truthy(fs.existsSync(outputMathified), formatSubprocessOutput(mathifyResult))

    const mathifyValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'validate-xhtml',
      bookId,
      'mathified-book',
      'collection.mathified.xhtml',
      'link-to-duplicate-id'
    ])
    await completion(mathifyValidateXhtml)

    const linkRexArchive = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'link-rex',
      bookId
    ])
    const linkRexArchiveResult = await completion(linkRexArchive)
    const outputRexLinkedArchive = `${outputDir}/${bookId}/rex-linked/${bookId}/collection.rex-linked.xhtml`
    t.truthy(fs.existsSync(outputRexLinkedArchive), formatSubprocessOutput(linkRexArchiveResult))

    const buildPdf = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'build-pdf',
      bookId
    ])
    const buildPdfResult = await completion(buildPdf)
    const outputPDF = `${outputDir}/${bookId}/artifacts/collection.pdf`
    const outputPDFUrl = `${outputDir}/${bookId}/artifacts/pdf_url`
    t.truthy(fs.existsSync(outputPDF), formatSubprocessOutput(buildPdfResult))
    t.is(fs.readFileSync(outputPDFUrl, { encoding: 'utf8' }), 'https://none.s3.amazonaws.com/collection.pdf', formatSubprocessOutput(buildPdfResult))
  })

  // Continue Archive Web Hosting Pipeline
  const checksum = spawn('node', [
    'src/cli/execute.js',
    ...commonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'checksum',
    bookId
  ])
  const branchArchiveWebHosting = completion(checksum).then(async (checksumResult) => {
    // checksum assertion
    const outputChecksum = `${outputDir}/${bookId}/checksum-book/${bookId}/resources`
    t.truthy(fs.existsSync(outputChecksum), formatSubprocessOutput(checksumResult))

    const checksumValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'validate-xhtml',
      bookId,
      'checksum-book',
      'collection.baked.xhtml',
      'link-to-duplicate-id'
    ])
    await completion(checksumValidateXhtml)

    const bakeMeta = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'bake-meta',
      bookId
    ])
    const bakeMetaResult = await completion(bakeMeta)
    const outputBakeMeta = `${outputDir}/${bookId}/baked-book-metadata/${bookId}/collection.baked-metadata.json`
    t.truthy(fs.existsSync(outputBakeMeta), formatSubprocessOutput(bakeMetaResult))

    const disassemble = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'disassemble',
      bookId
    ])
    const disassembleResult = await completion(disassemble)
    const outputDisassemble = `${outputDir}/${bookId}/disassembled-book/${bookId}/disassembled/collection.toc.xhtml`
    t.truthy(fs.existsSync(outputDisassemble), formatSubprocessOutput(disassembleResult))

    const disassembleValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'validate-xhtml',
      bookId,
      'disassembled-book',
      'disassembled/*@*.xhtml',
      'duplicate-id'
    ])
    await completion(disassembleValidateXhtml)

    const patchDisassembledLinks = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'patch-disassembled-links',
      bookId
    ])
    const patchDisassembledLinksResult = await completion(patchDisassembledLinks)
    const outputPatchDisassembleXHTML = `${outputDir}/${bookId}/disassembled-linked-book/${bookId}/disassembled-linked/collection.toc.xhtml`
    const outputPatchDisassembleJSON = `${outputDir}/${bookId}/disassembled-linked-book/${bookId}/disassembled-linked/collection.toc-metadata.json`
    t.truthy(fs.existsSync(outputPatchDisassembleXHTML), formatSubprocessOutput(patchDisassembledLinksResult))
    t.truthy(fs.existsSync(outputPatchDisassembleJSON), formatSubprocessOutput(patchDisassembledLinksResult))

    const patchDisassembledLinksValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'validate-xhtml',
      bookId,
      'disassembled-linked-book',
      'disassembled-linked/*@*.xhtml',
      'duplicate-id'
    ])
    await completion(patchDisassembledLinksValidateXhtml)

    const jsonify = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'jsonify',
      bookId
    ])
    const jsonifyResult = await completion(jsonify)
    const outputJsonify = `${outputDir}/${bookId}/jsonified-book/${bookId}/jsonified/collection.toc.json`
    t.truthy(fs.existsSync(outputJsonify), formatSubprocessOutput(jsonifyResult))

    const jsonifyValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      'validate-xhtml',
      bookId,
      'jsonified-book',
      'jsonified/*@*.xhtml',
      'duplicate-id'
    ])
    await completion(jsonifyValidateXhtml)

    const gdocify = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'gdocify',
      bookId
    ])
    await completion(gdocify)

    const convertDocx = spawn('node', [
      'src/cli/execute.js',
      ...commonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'convert-docx',
      bookId
    ])
    const convertDocxResult = await completion(convertDocx)
    const outputConvertIntro = `${outputDir}/${bookId}/docx-book/${bookId}/docx/1-introduction.docx`
    const outputConvertPreface = `${outputDir}/${bookId}/docx-book/${bookId}/docx/preface.docx`
    t.truthy(fs.existsSync(outputConvertPreface), formatSubprocessOutput(convertDocxResult))
    t.truthy(fs.existsSync(outputConvertIntro), formatSubprocessOutput(convertDocxResult))
  })

  // Start Running (Joint) Git Pipeline Tasks
  const gitCommonArgs = [
    'run',
    `--data=${gitOutputDir}`,
    '--persist'
  ]

  const gitValidateCnxml = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    'validate-cnxml',
    bookSlug,
    'fetched-book-group',
    'raw/modules/**/*.cnxml',
    'raw/collections/*.xml',
    '--contentsource=git'
  ])

  await completion(gitValidateCnxml)

  const gitAssemble = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    'assemble-group',
    bookSlug
  ])
  const gitAssembleResult = await completion(gitAssemble)
  const outputGitAssemble = `${gitOutputDir}/${bookSlug}/assembled-book-group/${bookSlug}.assembled.xhtml`
  t.truthy(fs.existsSync(outputGitAssemble), formatSubprocessOutput(gitAssembleResult))

  const gitAssembleMeta = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'assemble-meta-group',
    bookSlug
  ])
  const gitAssembleMetaResult = await completion(gitAssembleMeta)
  const outputGitAssembleMeta = `${gitOutputDir}/${bookSlug}/assembled-book-metadata-group/${bookSlug}.assembled-metadata.json`
  t.truthy(fs.existsSync(outputGitAssembleMeta), formatSubprocessOutput(gitAssembleMetaResult))

  const gitBake = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    'bake-group',
    bookSlug,
    `${dataDir}/col30149-recipe.css`,
    `${dataDir}/blank-style.css`
  ])
  const gitBakeResult = await completion(gitBake)
  const outputGitBake = `${gitOutputDir}/${bookSlug}/baked-book-group/${bookSlug}.baked.xhtml`
  t.truthy(fs.existsSync(outputGitBake), formatSubprocessOutput(gitBakeResult))

  const gitBakedValidateXhtml = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    'validate-xhtml',
    bookSlug,
    'baked-book-group',
    '*.baked.xhtml',
    'duplicate-id broken-link',
    '--contentsource=git'
  ])
  await completion(gitBakedValidateXhtml)

  const gitBakeMeta = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'bake-meta-group',
    bookSlug
  ])
  const gitBakeMetaResult = await completion(gitBakeMeta)
  const outputGitBakeMeta = `${gitOutputDir}/${bookSlug}/baked-book-metadata-group/${bookSlug}.baked-metadata.json`
  t.truthy(fs.existsSync(outputGitBakeMeta), formatSubprocessOutput(gitBakeMetaResult))

  const gitLinkSingle = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'link-single',
    bookSlug
  ])
  const gitLinkResult = await completion(gitLinkSingle)
  const outputGitLink = `${gitOutputDir}/${bookSlug}/linked-single/${bookSlug}.linked.xhtml`
  t.truthy(fs.existsSync(outputGitLink), formatSubprocessOutput(gitLinkResult))

  // Continue Git Web Hosting Pipeline
  const gitDisassemble = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'disassemble-single',
    bookSlug
  ])
  const branchGitWebHosting = completion(gitDisassemble).then(async (gitDisassembleResult) => {
    // dissemble assertion
    t.truthy(fs.existsSync(`${gitOutputDir}/${bookSlug}/disassembled-single/${bookSlug}.toc.xhtml`), formatSubprocessOutput(gitDisassembleResult))

    const gitPatchDisassembledLinks = spawn('node', [
      'src/cli/execute.js',
      ...gitCommonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'patch-disassembled-links-single',
      bookSlug
    ])
    const gitPatchDisassembledLinksResult = await completion(gitPatchDisassembledLinks)
    const outputGitPatchXHTML = `${gitOutputDir}/${bookSlug}/disassembled-linked-single/${bookSlug}.toc.xhtml`
    const outputGitPatchJSON = `${gitOutputDir}/${bookSlug}/disassembled-linked-single/${bookSlug}.toc-metadata.json`
    t.truthy(fs.existsSync(outputGitPatchXHTML), formatSubprocessOutput(gitPatchDisassembledLinksResult))
    t.truthy(fs.existsSync(outputGitPatchJSON), formatSubprocessOutput(gitPatchDisassembledLinksResult))

    const gitJsonify = spawn('node', [
      'src/cli/execute.js',
      ...gitCommonArgs,
      '--image=localhost:5000/openstax/cops-bakery-scripts:test',
      'jsonify-single',
      bookSlug
    ])
    const gitJsonifyResult = await completion(gitJsonify)
    const outputGitJsonifyXHTML = `${gitOutputDir}/${bookSlug}/jsonified-single/${bookSlug}.toc.xhtml`
    const outputGitJsonifyJSON = `${gitOutputDir}/${bookSlug}/jsonified-single/${bookSlug}.toc.json`
    t.truthy(fs.existsSync(outputGitJsonifyJSON), formatSubprocessOutput(gitJsonifyResult))
    t.truthy(fs.existsSync(outputGitJsonifyXHTML), formatSubprocessOutput(gitJsonifyResult))

    const gitJsonifiedValidateXhtml = spawn('node', [
      'src/cli/execute.js',
      ...gitCommonArgs,
      'validate-xhtml',
      bookSlug,
      'jsonified-single',
      '*@*.xhtml',
      '--contentsource=git'
    ])
    await completion(gitJsonifiedValidateXhtml)
  })

  // Continue Git PDF Pipeline
  const gitMathify = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    'mathify-single',
    bookSlug
  ])
  const gitMathifyResult = await completion(gitMathify)
  const outputGitMathify = `${gitOutputDir}/${bookSlug}/mathified-single/${bookSlug}.mathified.xhtml`
  t.truthy(fs.existsSync(outputGitMathify), formatSubprocessOutput(gitMathifyResult))

  const linkRexGit = spawn('node', [
    'src/cli/execute.js',
    ...gitCommonArgs,
    '--image=localhost:5000/openstax/cops-bakery-scripts:test',
    'link-rex',
    bookSlug
  ])
  const branchGitPDF = completion(linkRexGit).then(async (linkRexGitResult) => {
    const outputRexLinkedGit = `${gitOutputDir}/${bookSlug}/rex-linked/${bookSlug}.rex-linked.xhtml`
    t.truthy(fs.existsSync(outputRexLinkedGit), formatSubprocessOutput(linkRexGitResult))

    const gitBuildPdf = spawn('node', [
      'src/cli/execute.js',
      ...gitCommonArgs,
      'pdfify-single',
      bookSlug
    ])
    const gitBuildPdfResult = await completion(gitBuildPdf)
    const outputGitBuildPdf = `${gitOutputDir}/${bookSlug}/artifacts-single/collection.pdf`
    const outputGitPdfUrl = `${gitOutputDir}/${bookSlug}/artifacts-single/pdf_url`
    t.truthy(fs.existsSync(outputGitBuildPdf), formatSubprocessOutput(gitBuildPdfResult))
    t.is(fs.readFileSync(outputGitPdfUrl, { encoding: 'utf8' }), 'https://none.s3.amazonaws.com/collection.pdf', formatSubprocessOutput(gitBuildPdfResult))
  })

  await Promise.all([branchArchivePDF, branchArchiveWebHosting, branchGitPDF, branchGitWebHosting])
  t.pass()
})
