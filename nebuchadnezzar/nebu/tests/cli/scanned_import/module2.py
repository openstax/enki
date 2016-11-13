# -*- coding: utf-8 -*-
from ....cli.discovery import register_subcommand


def assign_args(parser):
    parser.add_argument('-h', '--humph', action='store_true')
    parser.add_argument('module2')


@register_subcommand('module2-command', assign_args, {'add_help': False})
def command(args):
    return args.module2
