# About

We build books in a pipeline of steps. These steps are written in different languages and sometimes run on a server and other times run locally.

In order to support both use-cases, all the steps are included in one Docker container and parameters are specified as environment variables.

Environment variables are used because each step may use different subsets of arguments and the author is not very familiar with parsing commandline arguments in bash.

Additionally, intput/output directores for each step are specified as environment variables because local development does not need different directories but the production buils in concourse-CI use different input/output directories for each step.


# Instructions

This uses a little wrapper to hide all the docker commands

```sh
# All-in-one
#
#  CLI   tempdir      command         col_id   recipe_name     version   server
./cli.sh ./data/fizix all-archive-pdf col12006 college-physics
./cli.sh ./data/socio all-archive-pdf col11407 sociology
./cli.sh ./data/socio all-archive-web col11407 sociology

# All-in-one Git-based books
#  CLI   tempdir         command     repo_name              gitref recipe      book_slug
./cli.sh ./data/tin-bk   all-git-pdf 'philschatz/tiny-book' main   chemistry   book-slug1
./cli.sh ./data/tin-bk   all-git-web 'philschatz/tiny-book' main   chemistry   book-slug1

# Private repositories: Set GH_SECRET_CREDS='..' before running ./cli.sh
```

# Run one step

If you want to run a single step at a time specify it as the first argument. Additional arguments are specified as environment variables.


```sh
# Common steps
ARG_COLLECTION_ID=col12006      ./cli.sh ./data/fizix archive-fetch
                                ./cli.sh ./data/fizix archive-assemble
                                ./cli.sh ./data/fizix archive-link-extras
ARG_RECIPE_NAME=college-physics ./cli.sh ./data/fizix archive-bake

# PDF steps
./cli.sh ./data/fizix archive-mathify
./cli.sh ./data/fizix archive-pdf

# Webhosting steps
./cli.sh ./data/fizix archive-assemble-metadata
./cli.sh ./data/fizix archive-bake-metadata
./cli.sh ./data/fizix archive-checksum
./cli.sh ./data/fizix archive-disassemble
./cli.sh ./data/fizix archive-patch-disassembled-links
./cli.sh ./data/fizix archive-jsonify
./cli.sh ./data/fizix archive-validate-xhtml
```

With the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.

## Environment Variables

This repository makes heavy use of environment variables. It uses them to pass information like which book and version to fetch as well as the directory to read/write to.

When running locally the directories by default read/write to subdirectories of [./data/](./data/) using a Docker volume mount. The pipelines that run in concourse use different directories since each one is an input/output directory specified in the Concourse-CI task.

### Directories

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

### Pipeline-specific Arguments

- `ARG_CODE_VERSION`
- `ARG_S3_BUCKET_NAME`

### Job-specific Arguments

- `ARG_RECIPE_NAME`
- `ARG_TARGET_PDF_FILENAME`

Only used for Git-based books:

- `ARG_GIT_REF` : the git branch name (e.g. `main`), tag, or specific commit (e.g. `@d34db33f`) you want to build
- `ARG_REPO_NAME` : the name of the GitHub repository that you want to build
- `ARG_TARGET_SLUG_NAME` : the book slug in the repository that you want to build

Only used for Legacy Archive-based books:

- `ARG_COLLECTION_ID` : the collection id of the book you want to build


### Optional Environment Variables

The CLI command (& docker steps) listen to a few optional environment variables, listed below with examples:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `TRACE_ON=1` | Debug | Set to anything to enable trace output
| `GH_SECRET_CREDS=user1:skjdhfs...` | Git Clone | An Authorization token from GitHub to clone a private repository
| `AWS_ACCESS_KEY_ID` | | AWS Upload | See `aws-access` for more
| `AWS_SECRET_ACCESS_KEY` | | AWS Upload | See `aws-access` for more
| `AWS_SESSION_TOKEN` | | AWS Upload | See `aws-access` for more

### Pipeline-generation Environment Variables

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
- [ ] Add the output-producer-resource repo into here
- [ ] add back support for content servers

## Future TODO work

- [ ] Read book list from `META-INF/books.xml` instead of `ls *.collection.xml` using xmlstarlet
- [ ] Consistent if;then, quotes (or not) around variables, and curly braces around variables
- [ ] Move everything out of the pipeline and into the image
