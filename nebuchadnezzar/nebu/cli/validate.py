from pathlib import Path

import click
from litezip import (
    parse_litezip,
    validate_litezip,
)

from ._common import common_params, logger


def is_valid(struct):
    """Checks validity of a litezip's contents with commandline ouput
    containing any validation errors.
    Returns True when the content is value and False if not.

    """

    has_errors = False
    cwd = Path('.').resolve()
    for filepath, error_msg in validate_litezip(struct):
        has_errors = True
        try:
            filepath = filepath.relative_to(cwd)
        except ValueError:
            # Raised ONLY when filepath is not a child of cwd
            pass
        logger.error('{}:{}'.format(filepath, error_msg))
    return not has_errors


@click.command()
@common_params
@click.argument('content_dir', default='.',
                type=click.Path(exists=True, file_okay=False))
def validate(content_dir):
    content_dir = Path(content_dir).resolve()
    struct = parse_litezip(content_dir)

    if is_valid(struct):
        logger.info("All good! :)")
    else:
        logger.info("We've got problems... :(")
