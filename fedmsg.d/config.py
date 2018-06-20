# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import logging


config = {
    'zmq_enabled': False,
    'endpoints': {},
    'validate_signatures': False,
    'stomp_heartbeat': 10000,
    'estuary_updater.enabled': True,
    'estuary_updater.log_level': logging.INFO,
    'estuary_updater.topics': [
        '/queue/Consumer.client-estuary-updater.dev.VirtualTopic.eng.freshmaker.event.state.changed',  # noqa: E501
        '/queue/Consumer.client-estuary-updater.dev.VirtualTopic.eng.freshmaker.build.state.changed'
    ],
    'estuary_updater.neo4j_url': 'bolt://neo4j:neo4j@localhost:7687',
    'estuary_updater.koji_url': 'http://kojihub.domain.com/kojihub',
    # Modify the values below
    'stomp_uri': 'server:61613',
    'stomp_ssl_crt': '/path/to/cert',
    'stomp_ssl_key': '/path/to/key'
}
