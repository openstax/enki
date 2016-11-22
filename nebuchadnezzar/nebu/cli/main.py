# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import click

from ..logger import configure_logging


__all__ = ('cli',)


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
    },
    'root': {
        'level': 'NOTSET',
        'handlers': [],
    },
}


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='enable verbosity')
def cli(verbose):
    set_verbosity(verbose)
