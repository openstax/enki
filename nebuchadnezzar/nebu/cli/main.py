# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import argparse

from ..logger import configure_logging
from .discovery import discover_subcommands


__all__ = ('main',)


console_logging_config = {
    'version': 1,
    'formatters': {
        'cli': {
            'format': '%(levelname)-5.5s: %(message)s',
            },
    },
    'filters': {},
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'cli',
            'filters': [],
            'stream': 'ext://sys.stdout',
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
    if verbose is None:
        config['loggers']['nebuchadnezzar']['level'] = 'ERROR'
    elif verbose:
        config['loggers']['nebuchadnezzar']['level'] = 'DEBUG'
    else:  # quiet
        config['loggers']['nebuchadnezzar']['level'] = 100
    configure_logging(config)


def create_main_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument(
        '-v', '--verbose', action='store_true',
        dest='verbose', default=None,
        help="increase verbosity")
    verbose_group.add_argument(
        '-q', '--quiet', action='store_false',
        dest='verbose', default=None,
        help="print nothing to stdout or stderr")

    discover_subcommands(parser)
    return parser


def main(argv=None):
    parser = create_main_parser()
    args = parser.parse_args(argv)
    set_verbosity(args.verbose)

    return args.cmd(args)
