# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals
import os

import pytest
from neomodel import config as neomodel_config, db as neo4j_db

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
