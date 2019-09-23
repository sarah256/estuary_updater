# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import
import os
from datetime import datetime

import pytest
from neomodel import config as neomodel_config, db as neo4j_db
from estuary.models.koji import KojiBuild, ContainerKojiBuild, KojiTag
import pytz
import koji

from estuary_updater.consumer import EstuaryUpdater


# Reinitialize Neo4j before each test
@pytest.fixture(autouse=True)
def run_before_tests():
    """Pytest fixture that prepares the environment before each test."""
    # Code that runs before each test
    neomodel_config.DATABASE_URL = os.environ.get(
        'NEO4J_BOLT_URL',
        'bolt://neo4j:neo4j@localhost:7687'
    )
    neomodel_config.AUTO_INSTALL_LABELS = True
    neo4j_db.cypher_query('MATCH (a) DETACH DELETE a')


@pytest.fixture(scope='session')
def consumer():
    """Pytest fixture that creates an EstuaryUpdater instance."""
    class FakeHub(object):
        """FakeHub to used to initialize a fedmsg consumer."""

        config = {}

    return EstuaryUpdater(FakeHub())


@pytest.fixture
def mock_getBuild_one():
    """Return a mock build in the format of koji.ClientSession.getBuild."""
    return {
        'completion_time': '2018-06-15 20:26:38.000000',
        'completion_ts': 1529094398.0,
        'creation_time': '2018-06-15 20:20:38.000000',
        'creation_ts': 1529094038.0,
        'epoch': 'epoch',
        'extra': {'container_koji_task_id': 17511743},
        'id': 710916,
        'name': 'e2e-container-test-product-container',
        'package_name': 'e2e-container-test-product-container',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'version': '7.4',
        'start_time': '2018-06-15 20:21:38.000000',
        'start_ts': 1529094098.0,
        'state': koji.BUILD_STATES['COMPLETE']
    }


@pytest.fixture
def mock_getBuild_complete():
    """Return a mock build in the format of koji.ClientSession.getBuild."""
    return {
        'completion_time': '2018-06-15 20:26:38.000000',
        'completion_ts': 1529094398.0,
        'creation_time': '2018-08-03 17:49:42.735510',
        'creation_ts': 1533318582.73551,
        'epoch': None,
        'extra': {'source': {'original_url': 'git://pkgs.domain.com/rpms/python-attrs?#3be3cb33e64'
                                             '32d8392ac3d9e6edffd990f618432'}},
        'id': 736244,
        'name': 'python-attrs',
        'package_name': 'python-attrs',
        'owner_name': 'emusk',
        'release': '8.el8+1325+72a36e76',
        'version': '17.4.0',
        'start_ts': 1533318582.73551,
        'start_time': '2018-08-03 17:49:42.735510',
        'state': koji.BUILD_STATES['COMPLETE']
    }


@pytest.fixture
def mock_getBuild_module_complete():
    """Return a mock build in the format of koji.ClientSession.getBuild."""
    return {
        'completion_time': '2018-08-17 16:54:17.000000',
        'completion_ts': 1534524857.0,
        'creation_time': '2018-08-17 16:54:29.130570',
        'creation_ts': 1534524869.13057,
        'epoch': None,
        'extra': {
            'typeinfo': {
                'module': {
                    'modulemd_str': 'module',
                    'name': 'virt',
                    'stream': 'rhel',
                    'module_build_service_id': 1648,
                    'version': '20180817161005',
                    'context': '9edba152',
                    'content_koji_tag': 'module-virt-rhel-20180817161005-9edba152'
                }
            }
        },
        'id': 753795,
        'name': 'virt',
        'package_name': 'virt',
        'owner_name': 'emusk',
        'release': '20180817161005.9edba152',
        'version': 'rhel',
        'start_time': '2018-08-17 16:10:29.000000',
        'start_ts': 1534522229.0,
        'state': koji.BUILD_STATES['COMPLETE']
    }


@pytest.fixture
def cb_one():
    """Return a KojiContainerBuild matching mock_getBuild_one."""
    return ContainerKojiBuild.get_or_create({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': {'container_koji_task_id': 17511743},
        'id_': '710916',
        'name': 'e2e-container-test-product-container',
        'package_name': 'openstack-zaqar-container',
        'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': 3,
        'version': '7.4'
    })[0]


@pytest.fixture
def kb_one():
    """Return a KojiBuild."""
    return KojiBuild.get_or_create({
        'completion_time': datetime(2018, 8, 3, 15, 13, 35, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 8, 3, 15, 9, 40, tzinfo=pytz.utc),
        'id_': '736088',
        'name': 'module-build-macros',
        'owner_name': 'emusk',
        'release': '1.el8+1318+37d5dc6c',
        'start_time': datetime(2018, 8, 3, 15, 9, 40, tzinfo=pytz.utc),
        'state': 1,
        'version': '0.1'
    })[0]


@pytest.fixture
def koji_tag():
    """Return a KojiTag."""
    return KojiTag.get_or_create({
        'id_': '15638',
        'name': 'rhos-13.0-rhel-7-pending'
    })[0]


@pytest.fixture
def module_build_getTag():
    """Return a KojiTag in the format of koji.ClientSession.getTag."""
    return {
        'id': '12233',
        'name': 'module-virt-rhel-20180817161005-9edba152'
    }


@pytest.fixture
def mock_cb_operator():
    """Return a container build that is an operator."""
    return {
        'completion_time': '2018-08-17 16:54:17.000000',
        'completion_ts': 1534524857.0,
        'creation_time': '2018-08-17 16:54:29.130570',
        'creation_ts': 1534524869.13057,
        'epoch': 'epoch',
        'id': '973358',
        'name': 'dv-operator-container',
        'owner_name': 'emusk',
        'package_name': 'dv-operator-container',
        'release': '2',
        'start_time': '2018-08-17 16:10:29.000000',
        'start_ts': 1534522229.0,
        'state': koji.BUILD_STATES['COMPLETE'],
        'version': '1.0',
        'extra': {
            'container_koji_task_id': 17511743,
            'typeinfo': {
                'operator-manifests': {
                    'archive': 'operator_manifests.zip'
                }
            }
        }
    }
