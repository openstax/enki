# -*- coding: utf-8 -*-
import versioneer
from setuptools import setup, find_packages


def parse_requirements(req_file):
    """Parse a requirements.txt file to a list of requirements"""
    with open(req_file, 'r') as fb:
        reqs = [
            req for req in fb.readlines()
            if req.strip() and not req.startswith('#')
        ]
    return list(reqs)


setup_requires = (
    'pytest-runner',
)
install_requires = parse_requirements('requirements/main.txt')
tests_require = parse_requirements('requirements/test.txt')
extras_require = {
    'test': tests_require,
    'tasks': 'neb-tasks',
}
description = "OpenStax Nebu publishing utility"
with open('README.rst', 'r') as readme:
    long_description = readme.read()

setup(
    name='nebuchadnezzar',
    version=versioneer.get_version(),
    author='OpenStax team',
    author_email='info@cnx.org',
    url="https://github.com/openstax/nebuchadnezzar",
    license='AGPL, See also LICENSE.txt',
    description=description,
    long_description=long_description,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    test_suite='nebu.tests',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'nebu.tests': ['data/**/*.*'],
    },
    cmdclass=versioneer.get_cmdclass(),
    entry_points="""\
    [console_scripts]
    neb = nebu.cli.main:cli
    """,
)
