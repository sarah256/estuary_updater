# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import logging


config = {
    'zmq_enabled': False,
    'endpoints': {},
    'validate_signatures': False,
    'stomp_heartbeat': 10000,
    'estuary_updater.enabled': True,
    'estuary_updater.log_level': logging.INFO,
    # Modify the values below
    'estuary_updater.topics': [
        # Make sure the consumer name is correct for your environment
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.freshmaker.event.state.changed',  # noqa: E501
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.freshmaker.build.state.changed',  # noqa: E501
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.distgit.commit',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.errata.activity.status',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.errata.activity.created'
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.errata.builds.added',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.errata.builds.removed',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.brew.build.complete',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.brew.build.building',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.brew.build.failed',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.brew.build.canceled',
        '/queue/Consumer.msg-client-estuary-updater.env.VirtualTopic.eng.brew.build.deleted',
    ],
    'stomp_ssl_crt': '/etc/estuary-updater/consumer.crt',
    'stomp_ssl_key': '/etc/estuary-updater/consumer.key',
    'estuary_updater.neo4j_url': 'bolt://neo4j:neo4j@localhost:7687',
    'estuary_updater.koji_url': 'http://kojihub.domain.com/kojihub',
    'estuary_updater.errata_url': 'https://errata.domain.com/',
    'stomp_uri': 'server:61613'
}
