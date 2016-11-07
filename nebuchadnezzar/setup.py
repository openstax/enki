# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup_requires = (
    'pytest-runner',
    )
install_requires = (
    'pathlib;python_version<="2.7"',
    )
tests_require = [
    'pytest',
    ]
extras_require = {
    'test': tests_require,
    }
description = "Connexions Berg publishing utility"
with open('README.rst', 'r') as readme:
    long_description = readme.read()

setup(
    name='berg',
    version='0.0.0',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/berg",
    license='LGPL, See also LICENSE.txt',
    description=description,
    long_description=long_description,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    test_suite='berg.tests',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'berg.tests': ['data/**/*.*'],
        },
    entry_points="""\
    [console_scripts]
    """,
    )
