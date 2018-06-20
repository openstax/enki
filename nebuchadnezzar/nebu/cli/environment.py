import click

from ._common import common_params, logger


@click.command(name='list')
@common_params
@click.pass_context
def list_environments(context):
    """List of valid environment names from config.

    Names are required for get and publish"""
    envs = context.obj['settings']['environs']
    lines = []
    for env, val in envs.items():
        lines.append('{}\t {url}'.format(env, **val))
    lines.sort()
    logger.info('\n'.join(lines))
