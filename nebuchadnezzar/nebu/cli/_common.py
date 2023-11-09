from functools import wraps

import click

from ..logger import configure_logging, logger


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
            'level': 'INFO',
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
        return func(*args, **kwargs)
    return wrapper


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:  # pragma: no cover
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)


__all__ = ['logger', 'common_params']
