# Instructions

This uses a little wrapper to hide all the docker commands

```sh
./cli.sh physics   fetch col12006
./cli.sh sociology fetch col11407

# Common steps
./cli.sh physics assemble
./cli.sh physics link-extras
./cli.sh physics bake college-physics # The recipe name

# PDF steps
./cli.sh physics mathify
./cli.sh physics pdf

# Webhosting steps
./cli.sh physics assemble-metadata
./cli.sh physics bake-metadata
./cli.sh physics checksum
./cli.sh physics disassemble
./cli.sh physics patch-disassembled-links
./cli.sh physics jsonify
./cli.sh physics validate-xhtml
```

In general, the format is:

```sh
TEMP_NAME=physics
# COL_ID=col12006
# RECIPE=college-physics

docker run -it -v $(pwd)/data/${TEMP_NAME}/:/data/ --rm my_image ${command} ${command_specific_args}
```

With the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.