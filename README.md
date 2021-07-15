# About

[![Codecov](https://img.shields.io/codecov/c/github/openstax/book-pipeline)](https://app.codecov.io/gh/openstax/book-pipeline) [![Gitpod](https://img.shields.io/badge/gitpod-ready%20to%20code-lightgrey)](https://gitpod.io/#https://github.com/openstax/book-pipeline)

We build books in a pipeline of steps. These steps are written in different languages and sometimes run on a server and other times run locally.

In order to support both use-cases, all the steps are included in one Docker container and parameters are specified as environment variables.

Environment variables are used because each step may use different subsets of arguments and the author is not very familiar with parsing commandline arguments in bash.

Additionally, intput/output directores for each step are specified as environment variables because local development does not need different directories but the production buils in concourse-CI use different input/output directories for each step.

The code is organized as follows:

- [Dockerfile](./Dockerfile) contains a multi-stage build and builds all the code necessary to build a PDF or the webhosting JSON
- [dockerfiles/docker-entrypoint.sh](./dockerfiles/docker-entrypoint.sh) contains the code for each step (e.g. fetch, assemble, bake, mathify) as well as convenience `all-*` steps which are only for local development
- [cli.sh](./cli.sh) is the start for developers building books locally on their machine
- [build-concourse/](./build-concourse/) contains scripts that generate Concourse pipeline YAML files which for each environment and pin the pipeline to a specific code version


## Specific Use-cases

- There is a [./cli.sh](./cli.sh) which is used to build books locally.
- In [build-concourse/](./build-concourse/) running `npm start` will generate Concourse Pipeline YAML files for the different CORGI environments (production, staging, local) and different webhosting environments (production, sandbox, local).


# Local Instructions

This uses a little wrapper to hide all the docker commands.

**Note:** If you are running this inside gitpod then you can replace `./cli.sh ./data/tin-bk/` with `./dockerfiles/docker-entrypoint.sh`

```sh
# All-in-one Git-based books
#  CLI   tempdir          command     repo_name/book_slug               recipe    gitref
./cli.sh ./data/tin-bk/   all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main
./cli.sh ./data/tin-bk/   all-git-web 'philschatz/tiny-book/book-slug1' chemistry main
# GH_SECRET_CREDS='..' before running ./cli.sh for private repositories

# All-in-one Archive-based books
#  CLI   tempdir       command         col_id   recipe          version   server
./cli.sh ./data/fizix/ all-archive-pdf col12006 college-physics latest
./cli.sh ./data/socio/ all-archive-pdf col11407 sociology       latest
./cli.sh ./data/socio/ all-archive-web col11407 sociology       latest
```

To upload DOCX files to **Google Docs** follow the [instructions here](./google-docs.md). To build a Google Docs pipeline, run `npm run build-gdocs` in [./build-concourse/](./build-concourse/)


## Run Tests

1. Run `./test.sh`
1. Open `./coverage/index.html` in a browser to see coverage


## Run one step

If you want to run a single step at a time specify it as the first argument.

```sh
# Common steps
./cli.sh ./data/socio/ local-create-book-directory col11407 sociology latest
./cli.sh ./data/socio/ archive-look-up-book
./cli.sh ./data/socio/ archive-fetch
./cli.sh ./data/socio/ archive-assemble
./cli.sh ./data/socio/ archive-link-extras
./cli.sh ./data/socio/ archive-bake

# PDF steps
./cli.sh ./data/socio/ archive-mathify
./cli.sh ./data/socio/ archive-pdf

# Concourse-only steps (AWS_ environemnt variables will likely need to be set)
ARG_CODE_VERSION='main' \
ARG_WEB_QUEUE_STATE_S3_BUCKET=openstax-sandbox-web-hosting-content-queue-state \
./cli.sh ./data/socio/ archive-report-book-complete
```

With the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.

## Run steps beginning with a step

Often developers will want to run all the steps beginning with a particular step.
This is commonly used in order to skip the fetch step_ since the book has already been fetched.

Use the `START_AT_STEP=` environment variable. Example:

```sh
START_AT_STEP=git-bake ./cli.sh ./data/tin-bk all-git-pdf
```

**Note:** The arguments following all-git-pdf can be omitted since they are only used in the initial step


# Environment Variables

[dockerfiles/docker-entrypoint.sh](./dockerfiles/docker-entrypoint.sh) specifically makes heavy use of environment variables. It uses them to pass information like which book and version to fetch as well as the directory to read/write to.

When running locally the directories by default read/write to subdirectories of [./data/](./data/) using a Docker volume mount. The pipelines that run in concourse use different directories since each one is an input/output directory specified in the Concourse-CI task.

## Pipeline-specific Arguments

- `ARG_CODE_VERSION`
- `ARG_S3_BUCKET_NAME`

## Job-specific Arguments

- `ARG_RECIPE_NAME`
- `ARG_TARGET_PDF_FILENAME`

Only used for Git-based books:

- `ARG_GIT_REF` : the git branch name (e.g. `main`), tag, or specific commit (e.g. `@d34db33f`) you want to build
- `ARG_REPO_NAME` : the name of the GitHub repository that you want to build
- `ARG_TARGET_SLUG_NAME` : the book slug in the repository that you want to build

Only used for Legacy Archive-based books:

- `ARG_COLLECTION_ID` : the collection id of the book you want to build

Only used for GoogleDocs (GDocs) pipeline:

- `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` : :warning: **How can developers create this?** [Maybe here](https://cloud.google.com/docs/authentication/production) but it's a different environment variable.
- `GDOC_GOOGLE_FOLDER_ID` : :warning: How can a dev find one of these for testing?

## Optional Environment Variables

The CLI command (& docker steps) listen to a few optional environment variables, listed below with examples:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `TRACE_ON` | Debug | Set to anything to enable trace output
| `CI` | Test | Collect code coverage |
| `GH_SECRET_CREDS=user1:skjdhfs...` | Git Clone | An Authorization token from GitHub to clone a private repository
| `AWS_ACCESS_KEY_ID` | | AWS Upload | See `aws-access` for more
| `AWS_SECRET_ACCESS_KEY` | | AWS Upload | See `aws-access` for more
| `AWS_SESSION_TOKEN` | | AWS Upload | See `aws-access` for more

## Pipeline-generation Environment Variables

The pipeline-generation code uses a few additional environment variables:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `CODE_VERSION=...` | | **Required:** The code version that the pipeline will use
| `DOCKERHUB_USERNAME` | | Your DockerHub username in case you are rate-limited
| `DOCKERHUB_PASSWORD` | | Your DockerHub password in case you are rate-limited


# CI/Gitpod Integration

This runs in GitHub Actions for CI reasons but... if we created a custom GitHub Action using this repo then all the books could use it to generate PDFs/web and post them somewhere (maybe using AWS/Google/Azure environment variables) and add a CI status link.

This runs in Gitpod but still needs a little work. Ideally, editing the files or checking out a different version of a submodule from within Gitpod should use that new code. Right now the Dockerfile contains all the instructions and the submodules are moved into an `/workspace/book-pipeline/` directory and various `~/.nvm/` directories are moved elsewhere.


# TODO list

- [x] Build Archive PDF
- [x] Build Archive JSON
- [x] Build Git PDF
- [x] Build Git JSON
- [x] Support checking out a commit instead of a branch/tag
- [x] Change entrypoint script to use environment variables for directories instead of assuming `/data/{name}`
    - search for `mv ` in build-concourse/script
- [x] Create a pipeline in concourse
- [x] Add the output-producer-resource repo into here
- [ ] add back support for content servers and content versions
- [x] verify the webhosting job uploaded: http://localhost:8080/teams/main/pipelines/webhosting/jobs/bakery/builds/4.1
- [x] verify the pipeline resource runs instead of the output-producer-resource
- [x] add the post-webhosting-push task of updating S3 to mark the job as done (check concourse-v6 for this task)
    - a.k.a. add webhosting "report book complete" task which uploads to the Queue bucket (yet another bucket)
- [x] combine gitTaskMaker and archiveTaskMaker into one generic taskMaker since the shell script will be tiny
- [x] add google docs pipeline-generation
- [x] auto-build a dependency graph image for documentation [./build-concourse/graphs/](./build-concourse/graphs/)
- [x] auto-build the bash script
- [x] wire up codecov.io ([Example](https://codecov.io/gh/openstax/book-pipeline/src/85ee2ea16a401ca07067af699350157b29bdc763/dockerfiles/docker-entrypoint.sh))
- [x] move all the steps into a JSON file so it can be parsed in node and bash
- [x] move the bash code for each step into a separate bash file and ensure codecov checks it
- [x] make the docker-entrypoint script use the JSON file to validate inputs, environment variables, and run the correct step
- [x] add code coverage for the TypeScript files
- [x] Move everything out of the pipeline and into the image
- [x] shellcheck the bash scripts (`shellcheck --severity=warning ./dockerfiles/steps/*`)
- [x] make it easy to rebuild and run inside gitpod (inside the container). Requires moving commands in Dockerfile into scripts again
- [ ] webhosting for git books
- [ ] remove the `git-` prefix from tasks so they wil ljust work when we remove archive tasks
- [ ] remove virtualenv and install python packages to the system (unless it's bad practice)

## Future TODO work

- [ ] shellcheck entrypoint bash scripts
- [ ] Read book list from `META-INF/books.xml` instead of `ls *.collection.xml` using xmlstarlet
- [ ] Consistent if;then, quotes (or not) around variables, and curly braces around variables
- [ ] move pm2 into bakery-scripts/ instead of being installed globally in the Dockerfile
- [ ] move auth secret rotation into this repo. See https://github.com/openstax/output-producer-service/pull/355
