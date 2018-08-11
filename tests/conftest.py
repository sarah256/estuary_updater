# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import
import os
from datetime import datetime

import pytest
from neomodel import config as neomodel_config, db as neo4j_db
from estuary.models.koji import ContainerKojiBuild
import pytz
import koji

from estuary_updater.consumer import EstuaryUpdater


neomodel_config.DATABASE_URL = os.environ.get('NEO4J_BOLT_URL', 'bolt://neo4j:neo4j@localhost:7687')
neomodel_config.AUTO_INSTALL_LABELS = True


# Reinitialize Neo4j before each test
@pytest.fixture(autouse=True)
def run_before_tests():
    """Pytest fixture that prepares the environment before each test."""
    # Code that runs before each test
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
        'completion_ts': 1529094398.0,
        'creation_ts': 1529094038.0,
        'epoch': 'epoch',
        'extra': {'container_koji_task_id': 17511743},
        'id': 710916,
        'name': 'e2e-container-test-product-container',
        'package_name': 'e2e-container-test-product-container',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'version': '7.4',
        'start_ts': 1529094098.0,
        'state': koji.BUILD_STATES['COMPLETE']
    }


@pytest.fixture
def cb_one():
    """Return a KojiContainerBuild matching mock_getBuild_one."""
    return ContainerKojiBuild.get_or_create({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': '{"container_koji_task_id": 17511743}',
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
