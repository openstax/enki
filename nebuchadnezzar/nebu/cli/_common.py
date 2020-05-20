from functools import wraps
from urllib.parse import urlparse, urlunparse
import hashlib

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
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
        'litezip': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': 0,
        },
        'cnxepub': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagte': 0,
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
        if '://' in environ_name:
            # Assume name is fqdn with protocol
            return environ_name
        if '.' in environ_name:
            # Assume name is fqdn sans protocol
            return f'https://{environ_name}'
        # Assume name is shortname for cnx host
        return f'https://{environ_name}.cnx.org'


def build_archive_url(context, environ_name):
    # Build the archive base url

    # We check to see if the archive URL has been specified in the
    # configuration settings. If so, we'll return that value. Otherwise we'll
    # fallback to the backwards compatible method of constructing based upon
    # convention.
    settings_archive_url = context.obj['settings']['environs'].get(
        environ_name,
        {}
    ).get(
        'archive_url'
    )

    if settings_archive_url:
        return settings_archive_url

    archive_url = get_base_url(context, environ_name)
    parsed_url = urlparse(archive_url)
    sep = len(parsed_url.netloc.split('.')) > 2 and '-' or '.'
    url_parts = [
        parsed_url.scheme,
        'archive{}{}'.format(sep, parsed_url.netloc),
    ] + list(parsed_url[2:])
    archive_url = urlunparse(url_parts)
    return archive_url


def set_verbosity(verbose):
    config = console_logging_config.copy()
    if verbose:
        level = 'DEBUG'
    else:
        level = 'INFO'
    config['loggers']['nebuchadnezzar']['level'] = level
    configure_logging(config)


def calculate_sha1(fpath):
    sha1 = hashlib.sha1()
    sha1.update(fpath.open('rb').read())
    return sha1.hexdigest()
