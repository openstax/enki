# About

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

There is a [./cli.sh](./cli.sh) which is used to build books locally.

In [build-concourse/](./build-concourse/) running `npm start` will generate Concourse Pipeline YAML files for the different CORGI environments (production, staging, local) and different webhosting environments (production, sandbox, local).


# Local Instructions

This uses a little wrapper to hide all the docker commands

```sh
# All-in-one
#
#  CLI   tempdir      command         col_id   recipe_name     version   server
./cli.sh ./data/fizix all-archive-pdf col12006 college-physics latest
./cli.sh ./data/socio all-archive-pdf col11407 sociology       latest
./cli.sh ./data/socio all-archive-web col11407 sociology       latest

# All-in-one Git-based books
#  CLI   tempdir         command     repo_name/book_slug               recipe    gitref
./cli.sh ./data/tin-bk   all-git-pdf 'philschatz/tiny-book/book-slug1' chemistry main
./cli.sh ./data/tin-bk   all-git-web 'philschatz/tiny-book/book-slug1' chemistry main

# Private repositories: Set GH_SECRET_CREDS='..' before running ./cli.sh
```

## Run one step

If you want to run a single step at a time specify it as the first argument. Additional arguments are specified as environment variables.


```sh
# Common steps
./cli.sh ./data/socio local-create-book-directory col11407 sociology latest
./cli.sh ./data/socio archive-look-up-book
./cli.sh ./data/socio archive-fetch
./cli.sh ./data/socio archive-assemble
./cli.sh ./data/socio archive-link-extras
./cli.sh ./data/socio archive-bake

# PDF steps
./cli.sh ./data/socio archive-mathify
./cli.sh ./data/socio archive-pdf

# Webhosting steps
./cli.sh ./data/socio archive-assemble-metadata
./cli.sh ./data/socio archive-bake-metadata
./cli.sh ./data/socio archive-checksum
./cli.sh ./data/socio archive-disassemble
./cli.sh ./data/socio archive-patch-disassembled-links
./cli.sh ./data/socio archive-jsonify
./cli.sh ./data/socio archive-validate-xhtml

# Concourse-only steps (AWS_ environemnt variables will likely need to be set)
ARG_CODE_VERSION='main' ARG_WEB_QUEUE_STATE_S3_BUCKET=openstax-sandbox-web-hosting-content-queue-state ./cli.sh ./data/socio archive-report-book-complete
```

With the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.

# Environment Variables

This repository makes heavy use of environment variables. It uses them to pass information like which book and version to fetch as well as the directory to read/write to.

When running locally the directories by default read/write to subdirectories of [./data/](./data/) using a Docker volume mount. The pipelines that run in concourse use different directories since each one is an input/output directory specified in the Concourse-CI task.

## Directories

Archive-specific:

- `IO_ARCHIVE_FETCHED`: ./data/raw
- `IO_ARCHIVE_BOOK`: ./data/assembled
- `IO_ARCHIVE_JSONIFIED`: ./data/jsonified
- `IO_ARCHIVE_UPLOAD`: ./data/upload

Git-specific:

- `IO_RESOURCES`: ./data/resources/
- `IO_UNUSED`: ./data/unused-resources/
- `IO_FETCHED`: ./data/fetched-book-group/
- `IO_ASSEMBLED`: ./data/assembled-book-group/
- `IO_ASSEMBLE_META`: ./data/assembled-metadata-group/
- `IO_BAKED`: ./data/baked-book-group/
- `IO_BAKE_META`: ./data/baked-metadata-group/
- `IO_LINKED`: ./data/linked-single/
- `IO_MATHIFIED`: ./data/mathified-single/
- `IO_DISASSEMBLED`: ./data/disassembled-single/
- `IO_ARTIFACTS`: ./data/artifacts-single/
- `IO_DISASSEMBLE_LINKED`: ./data/disassembled-linked-single/
- `IO_JSONIFIED`: ./data/jsonified-single/

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


## Optional Environment Variables

The CLI command (& docker steps) listen to a few optional environment variables, listed below with examples:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `TRACE_ON=1` | Debug | Set to anything to enable trace output
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

## Future TODO work

- [ ] Read book list from `META-INF/books.xml` instead of `ls *.collection.xml` using xmlstarlet
- [ ] Consistent if;then, quotes (or not) around variables, and curly braces around variables
- [ ] Move everything out of the pipeline and into the image
