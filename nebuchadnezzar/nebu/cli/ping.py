import sys

import click
import requests
from requests.auth import HTTPBasicAuth

from ._common import common_params, get_base_url, logger


@click.command()
@common_params
@click.argument('env')
@click.option('-u', '--username', type=str, prompt=True)
@click.option('-p', '--password', type=str, prompt=True, hide_input=True)
@click.option('-k', '--insecure', is_flag=True, default=False,
              help="Ignore SSL certificate verification errors")
@click.pass_context
def ping(ctx, env, username, password, insecure):
    """Check credentials and permission to publish on server"""
    base_url = get_base_url(ctx, env)

    auth = HTTPBasicAuth(username, password)
    auth_ping_url = '{}/api/auth-ping'.format(base_url)
    auth_ping_resp = requests.get(
        auth_ping_url,
        auth=auth,
        verify=not insecure
    )

    if auth_ping_resp.status_code == 401:
        logger.error('Bad credentials: \n{}'.format(
            auth_ping_resp.content.decode('utf-8')))
        sys.exit(1)
    elif auth_ping_resp.status_code != 200:
        logger.error('Server error (status code: {})\n{}'.format(
            auth_ping_resp.status_code,
            auth_ping_resp.content.decode('utf-8')))
        sys.exit(1)

    publish_ping_url = '{}/api/publish-ping'.format(base_url)
    publish_ping_resp = requests.get(
        publish_ping_url,
        auth=auth,
        verify=not insecure
    )

    if publish_ping_resp.status_code == 401:
        logger.error('Publishing not allowed: \n{}'.format(
            publish_ping_resp.content.decode('utf-8')))
        sys.exit(1)
    elif publish_ping_resp.status_code != 200:
        logger.error('Server error (status code: {})\n{}'.format(
            publish_ping_resp.status_code,
            publish_ping_resp.content.decode('utf-8')))
        sys.exit(1)

    logger.info('The user has permission to publish on this server.')
