# -*- coding: utf-8 -*-
import argparse
try:
    from unittest import mock
except ImportError:
    import mock

import pytest
import venusian


@pytest.fixture
def parser():
    return argparse.ArgumentParser()


@pytest.fixture
def sub_parsers(parser):
    sub_parser = parser.add_subparsers()
    return mock.Mock(spec=sub_parser)


@pytest.fixture
def scanner(sub_parsers):
    return venusian.Scanner(sub_parsers=sub_parsers)


def test_registration(scanner, sub_parsers):
    from . import scanned_import
    from ...cli.discovery import SUBCOMMAND_CATEGORY as category
    scanner.scan(scanned_import, categories=(category,))

    assert sub_parsers.add_parser.call_count == 2

    sub_parsers.add_parser.assert_any_call('module1-command')
    func = scanned_import.module1.command
    sub_parsers.add_parser.assert_has_calls([
        mock.call().set_defaults(cmd=func),
    ])

    sub_parsers.add_parser.assert_any_call('module2-command', add_help=False)
    func = scanned_import.module2.command
    sub_parsers.add_parser.assert_has_calls([
        mock.call().set_defaults(cmd=func),
    ])
    sub_parsers.add_parser.assert_has_calls([
        mock.call().add_argument('module2'),
    ])


def test_discovery(parser):
    from . import scanned_import
    from ...cli.discovery import discover_subcommands
    discover_subcommands(parser, scope=scanned_import)

    args = parser.parse_args(['module1-command'])
    assert args.cmd(args)

    test_arg = 'echo'
    args = parser.parse_args(['module2-command', test_arg])
    assert args.cmd(args) == test_arg
