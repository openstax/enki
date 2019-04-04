from pathlib import Path
import re

import click
import docker

from ..logger import logger
from ._common import common_params


IMAGE_TAG = 'openstax/mathify'
REPO_URL = 'https://github.com/openstax/mathify.git'
INPUT_FILE = 'collection.assembled.xhtml'
OUTPUT_FILE = 'collection.mathified.xhtml'
MOUNT_POINT = '/out'


@click.command()
@common_params
@click.option('-f', '--format', default='svg',
              help='The format that math should transform to')
@click.option('--build', is_flag=True,
              help='Force build the baked-pdf image even if the image exists')
@click.option('-i', '--input-file', type=click.Path(exists=True),
              help=("Location of the input file"))
@click.argument('collection_path', type=click.Path())
@click.pass_context
def mathify(ctx, collection_path, build, input_file, format):
    """Transform math in COLLECTION_PATH to svg or html"""
    colpath = Path(collection_path)
    if input_file:
        input_file = Path(input_file)
    else:
        input_file = colpath / INPUT_FILE

    if not input_file.is_file():
        raise ValueError('Input file {} not found or is not a file.'.format(
            input_file))

    output_file = input_file.parent / OUTPUT_FILE
    # If input_file is
    # ./col12345_1.23.45/Introductory Statistics/collection.xhtml, then
    # mounted_input_file will be
    # /out/Introductory Statistics/collection.xhtml
    # It replaces the top parent "col12345_1.23.45" with the mount point /out
    mounted_input_file = MOUNT_POINT / input_file.relative_to(colpath)
    mounted_output_file = mounted_input_file.parent / OUTPUT_FILE

    client = docker.from_env()
    try:
        client.images.pull(IMAGE_TAG)
    except docker.errors.ImageNotFound:
        # the image might eventually be available on docker hub, but if it's
        # not available, we can build the image ourselves
        pass
    images = client.images.list(IMAGE_TAG)
    if not images or build:
        logger.info('Building the {} image...'.format(IMAGE_TAG))
        # docker build -t openstax/cnx-bakedpdf \
        #    https://github.com/openstax/baked-pdf.git
        image, build_logs = client.images.build(
            path=REPO_URL, tag=IMAGE_TAG, rm=True)
        for log in build_logs:
            if 'stream' in log:
                logger.debug(log['stream'])

    # collection.mathified.html has resources pointing to the mathjax node
    # module, which only exist in the container.  We need to copy out the files
    # and change the resource urls.
    mathify_command = "node typeset/start -i '{}' -o '{}' -f {}".format(
        mounted_input_file, mounted_output_file, format)
    copy_mathjax_resources = "cp -r node_modules/mathjax '{}'".format(
        mounted_input_file.parent)
    chmod_output = "chmod a+w '{}'".format(mounted_output_file)
    command = ' && '.join([mathify_command, copy_mathjax_resources,
                           chmod_output])
    # docker run --rm openstax/cnx-bakedpdf
    #    --mount type=bind,source=col12345_1.23.45,target=/out
    #    /bin/bash -c \
    #    "cp -r node_modules/mathjax /out/data/ && \
    #     node typeset/start -i /out/data/collection.xhtml \
    #                        -o /out/data/collection.mathified.xhtml \
    #                        -f $MATH_FORMAT"
    logger.debug('command: {}'.format(command))
    run_logs = client.containers.run(
        IMAGE_TAG, command='/bin/bash -c "{}"'.format(command), remove=True,
        mounts=[
            docker.types.Mount(target=MOUNT_POINT,
                               source=str(colpath.absolute()), type='bind')])
    logger.debug(run_logs.decode('utf-8'))
    with output_file.open('r') as f:
        content = f.read()
    with output_file.open('w') as f:
        f.write(re.sub('(file://)?/src/node_modules/', '', content))
    logger.info('Math converted to {} in {}'.format(format, output_file))
