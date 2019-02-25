import os

import click
from cnxtransforms import cnxml_to_full_html

from ._common import common_params


@click.command()
@common_params
@click.argument('collection_path')
def cnxml_to_html(collection_path):
    """Given a collection COLLECTION_PATH (downloaded using neb get or complete
    zip on the cnx site), transform all the index.cnxml to index.cnxml.html"""

    for root, dirs, files in os.walk(collection_path):
        if 'index.cnxml' in files:
            index_cnxml_path = os.path.join(root, 'index.cnxml')
            with open(index_cnxml_path) as f:
                index_cnxml = f.read()
            with open('{}.html'.format(index_cnxml_path), 'w') as f:
                f.write(cnxml_to_full_html(index_cnxml))
