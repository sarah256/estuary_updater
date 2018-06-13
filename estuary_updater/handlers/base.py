# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import abc

import neomodel

from estuary_updater import log


class BaseHandler(object):
    """An abstract base class for handlers to enforce the API."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Initialize the handler.

        :param dict config: the fedmsg configuration
        """
        self.config = config
        if config.get('estuary_updater.neo4j_url'):
            neomodel.config.DATABASE_URL = config['estuary_updater.neo4j_url']
        else:
            log.warn('The configuration "estuary_updater.neo4j_url" was not set, so the default '
                     'will be used')
            neomodel.config.DATABASE_URL = 'bolt://neo4j:neo4j@localhost:7687'

    @staticmethod
    @abc.abstractmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def handle(self, msg):
        """
        Handle a message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        pass
