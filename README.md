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

If you want to run a single step at a time specify it as the first argument. Subsequent arguments are specific to that step.


```sh
# Common steps
./cli.sh ./data/fizix archive-fetch col12006
./cli.sh ./data/fizix archive-assemble
./cli.sh ./data/fizix archive-link-extras
./cli.sh ./data/fizix archive-bake college-physics # The recipe name

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

The CLI command (& docker steps) listen to a few optional environment variables, listed below with examples:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `TRACE_ON=1` | Debug | Set to anything to enable trace output
| `GH_SECRET_CREDS=user1:skjdhfs...` | Git Clone | An Authorization token from GitHub to clone a private repository
| `AWS_ACCESS_KEY_ID` | | AWS Upload | See `aws-access` for more
| `AWS_SECRET_ACCESS_KEY` | | AWS Upload | See `aws-access` for more
| `AWS_SESSION_TOKEN` | | AWS Upload | See `aws-access` for more


# TODO list

- [x] Build Archive PDF
- [x] Build Archive JSON
- [x] Build Git PDF
- [x] Build Git JSON
- [x] Support checking out a commit instead of a branch/tag
- [ ] Change entrypoint script to use environment variables for directories instead of assuming `/data/{name}`
    - search for `mv ` in build-concourse/script
- [ ] Read book list from `META-INF/books.xml` instead of `ls *.collection.xml` using xmlstarlet
- [ ] Consistent if;then, quotes (or not) around variables, and curly braces around variables
- [ ] add back support for content servers
- [x] Create a pipeline in concourse
- [ ] Answer the following: When should code be in the image vs in the pipeline? (The pipeline should be as little as possible)
- [ ] Answer the following: When should data be passed into docker via environment variable vs argument vs file?
    - Environment:
        - AWS secrets
        - Input/Output directories (like IO_JSONIFIED=/data/jsonified by default but pipeline would set it to be different)
    - (maybe everything except the command to run?)