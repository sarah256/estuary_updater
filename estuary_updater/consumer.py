# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import fedmsg.consumers

from estuary_updater import config, log, version
from estuary_updater.handlers import all_handlers


class EstuaryUpdater(fedmsg.consumers.FedmsgConsumer):
    """The consumer that handles all incoming messages for Estuary Updater."""

    topic = config.get('estuary_updater.topics', [])
    config_key = 'estuary_updater.enabled'

    def __init__(self, *args, **kw):
        """Initialize the consumer."""
        log.info('Starting up Estuary Updater v{0}'.format(version))
        super(EstuaryUpdater, self).__init__(*args, **kw)

    def consume(self, msg):
        """
        Process a message from the message bus.

        :param dict msg: a received message from the message bus
        """
        # Try to find a handler that can handle this type of message
        for handler_cls in all_handlers:
            if handler_cls.can_handle(msg):
                log.debug('The handler {0} supports handling the message: {1}'.format(
                    handler_cls.__name__, msg))
                handler = handler_cls(config)
                log.debug('The handler {0} is instantiated and will handle the message: {1}'.format(
                    handler_cls.__name__, msg))
                handler.handle(msg)
                log.debug('The handler {0} is done handling the message: {1}'.format(
                    handler_cls.__name__, msg))
