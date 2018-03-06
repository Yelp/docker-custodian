# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from docker_custodian.__about__ import __version__


setup(
    name='docker_custodian',
    version=__version__,
    provides=['docker_custodian'],
    author='Daniel Nephin',
    author_email='dnephin@yelp.com',
    description='Keep docker hosts tidy.',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    install_requires=[
        'python-dateutil',
        'docker',
        'pytimeparse',
    ],
    license="Apache License 2.0",
    entry_points={
        'console_scripts': [
            'dcstop = docker_custodian.docker_autostop:main',
            'dcgc = docker_custodian.docker_gc:main',
        ],
    },
)
