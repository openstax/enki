from functools import wraps

import click

from ..logger import configure_logging, logger
from .exceptions import UnknownEnvironment


console_logging_config = {
    'version': 1,
    'formatters': {
        'cli': {
            'format': '%(message)s',
        },
    },
    'filters': {},
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'cli',
            'filters': [],
            'stream': 'ext://sys.stderr',
        },
    },
    'loggers': {
        'nebuchadnezzar': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
        'litezip': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
    },
    'root': {
        'level': 'NOTSET',
        'handlers': [],
    },
}


def common_params(func):
    @click.option('-v', '--verbose', is_flag=True, help='enable verbosity')
    @click.pass_context
    @wraps(func)
    def wrapper(ctx, verbose, *args, **kwargs):
        set_verbosity(verbose)
        logger.debug('Using the configuration file at {}'
                     .format(ctx.obj['settings']['_config_file']))
        return func(*args, **kwargs)
    return wrapper


def confirm(prompt="OK to continue? [Y/N] "):
    """
    Ask for Y/N answer.
    returns bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input(prompt).lower()
    return answer == "y"


def get_base_url(context, environ_name):
    try:
        return context.obj['settings']['environs'][environ_name]['url']
    except KeyError:
        raise UnknownEnvironment(environ_name)


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)
