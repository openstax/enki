from pathlib import Path

import click
import pkg_resources

from ._common import common_params, logger


_confirmation_prompt = (
    'A backup of your atom-config will be created.\n'
    'However, this will overwrite your config... continue?'
)
_ATOM_CONFIG_TEMPLATE = """\
"*":
  core:
    customFileTypes:

      # Add this to the bottom of the customFileTypes area.
      # Note: Indentation is important!
      "text.xml": [
        "index.cnxml"
      ]


  # And then this to the bottom of the file
  # 1. Make sure "linter-autocomplete-jing" only occurs once in this file!
  # 1. make sure it is indented by 2 spaces just like it is in this example.

  "linter-autocomplete-jing":
    displaySchemaWarnings: true
    rules: [
      {
        priority: 1
        test:
          pathRegex: ".cnxml$"
        outcome:
          schemaProps: [
            {
              lang: "rng"
              path: "%s"
            }
          ]
      }
    ]
"""


@click.command(name='config-atom')
@common_params
@click.confirmation_option(prompt=_confirmation_prompt)
def config_atom():
    filepath = Path.home() / '.atom/config.cson'
    if not filepath.parent.exists():
        filepath.parent.mkdir()
    if filepath.exists():
        backup_filepath = filepath.parent / 'config.cson.bak'
        filepath.rename(backup_filepath)
        logger.info("Wrote backup to {}".format(backup_filepath.resolve()))

    cnxml_jing_rng = pkg_resources.resource_filename(
        'cnxml',  # find by package name
        'xml/cnxml/schema/rng/0.7/cnxml-jing.rng')
    with filepath.open('w') as fb:
        fb.write(_ATOM_CONFIG_TEMPLATE % cnxml_jing_rng)

    logger.info("Wrote {}".format(filepath.resolve()))
