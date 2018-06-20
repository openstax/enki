import click


__all__ = (
    'ExistingOutputDir',
    'MissingContent',
    'OldContent',
    'UnknownEnvironment',
)


class ExistingOutputDir(click.ClickException):
    exit_code = 3

    def __init__(self, output_dir):
        message = "directory already exists:  {}".format(output_dir)
        super(ExistingOutputDir, self).__init__(message)


class MissingContent(click.ClickException):
    exit_code = 4

    def __init__(self, id, version):
        message = "content unavailable for '{}/{}'".format(id, version)
        super(MissingContent, self).__init__(message)


class OldContent(click.ClickException):
    exit_code = 6

    def __init__(self):
        message = "Non-latest version requested"
        super(OldContent, self).__init__(message)


class UnknownEnvironment(click.ClickException):
    exit_code = 5

    def __init__(self, environ_name):
        message = "unknown environment '{}'".format(environ_name)
        super(UnknownEnvironment, self).__init__(message)
