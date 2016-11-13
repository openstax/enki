# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import argparse

from .discovery import discover_subcommands


__all__ = ('main',)



def create_main_parser():
    parser = argparse.ArgumentParser(description=__doc__)

    discover_subcommands(parser)
    return parser


def main(argv=None):
    parser = create_main_parser()
    args = parser.parse_args(argv)

    return args.cmd(args)
