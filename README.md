# Instructions

This uses a little wrapper to hide all the docker commands

```sh
# All-in-one
#
#  CLI   tempdir   command         col_id   recipe_name 
./cli.sh fizix     all-archive-pdf col12006 college-physics
./cli.sh socio     all-archive-pdf col11407 sociology
./cli.sh socio     all-archive-web col11407 sociology

# All-in-one Git-based books
#  CLI   tempdir  command     repo_name              gitref recipe      book_slug
./cli.sh tin-bk   all-git-pdf 'philschatz/tiny-book' main   chemistry   book-slug1

# Private repositories: Set GH_SECRET_CREDS='..' before running ./cli.sh
```

# Run one step

If you want to run a single step at a time specify it as the first argument. Subsequent arguments are specific to that step.


```sh
# Common steps
./cli.sh fizix archive-fetch col12006
./cli.sh fizix archive-assemble
./cli.sh fizix archive-link-extras
./cli.sh fizix archive-bake college-physics # The recipe name

# PDF steps
./cli.sh fizix archive-mathify
./cli.sh fizix archive-pdf

# Webhosting steps
./cli.sh fizix archive-assemble-metadata
./cli.sh fizix archive-bake-metadata
./cli.sh fizix archive-checksum
./cli.sh fizix archive-disassemble
./cli.sh fizix archive-patch-disassembled-links
./cli.sh fizix archive-jsonify
./cli.sh fizix archive-validate-xhtml
```

With the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.

## Environment Variables

The CLI command (& docker steps) listen to a few optional environment variables, listed below with examples:

| Name | Use | Description |
| :--- | :-- | :---------- |
| `DATA_ROOT=$(pwd)/data` | temp | Directory on where the generated files are stored (on the host)
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
- [ ] Read book list from `META-INF/books.xml` instead of `ls *.collection.xml` using xmlstarlet
- [ ] Consistent if;then, quotes (or not) around variables, and curly braces around variables
- [ ] add back support for content servers