# Instructions

This uses a little wrapper to hide all the docker commands

```sh
./cli.sh physics   fetch col12006
./cli.sh sociology fetch col11407

./cli.sh physics assemble
./cli.sh physics link-extras
./cli.sh physics bake college-physics # The recipe name
./cli.sh physics mathify
./cli.sh physics pdf
```

In general, the format is:

```sh
TEMP_NAME=physics
# COL_ID=col12006
# RECIPE=college-physics

docker run -it -v $(pwd)/data/${TEMP_NAME}/:/data/ --rm my_image ${command} ${command_specific_args}
```

And with the above command, docker will use the `$(pwd)/data/${TEMP_NAME}/` directory to read/write files during each step.