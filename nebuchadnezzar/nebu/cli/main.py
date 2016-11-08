# -*- coding: utf-8 -*-
"""Commandline utility for publishing content"""
import argparse


__all__ = ('main',)



def create_main_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    return parser


def main(argv=None):
    parser = create_main_parser()
    args = parser.parse_args(argv)

    return args.cmd(args)
