# SPDX-License-Identifier: GPL-3.0+

from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

setup(
    name='estuary_updater',
    version='0.1',
    description='A micro-service that updates the graph database in real-time for Estuary',
    author='Red Hat, Inc.',
    author_email='mprahl@redhat.com',
    license='GPLv3+',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=requirements,
    entry_points="""
    [moksha.consumer]
    estuary_updater = estuary_updater.consumer:EstuaryUpdater
    """
)
