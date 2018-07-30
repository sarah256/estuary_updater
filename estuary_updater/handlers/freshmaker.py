# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import neomodel
from estuary.models.freshmaker import FreshmakerEvent
from estuary.models.errata import Advisory
import koji
from estuary.models.koji import ContainerKojiBuild, KojiBuild

from estuary_updater.handlers.base import BaseHandler
from estuary_updater import log


class FreshmakerHandler(BaseHandler):
    """A handler for Freshmaker-related messages."""

    # Translates the Freshmaker build state to its equivalent in Koji
    freshmaker_to_koji_states = {
        0: 0,
        1: 1,
        2: 3
    }

    @staticmethod
    def can_handle(msg):
        """
        Determine if the message is a Freshmaker-related message and can be handled by this handler.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        supported_topics = [
            '/topic/VirtualTopic.eng.freshmaker.event.state.changed',
            '/topic/VirtualTopic.eng.freshmaker.build.state.changed'
        ]

        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a Freshmaker message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        topic = msg['topic']
        self.koji_session = koji.ClientSession(self.config['estuary_updater.koji_url'])

        if topic == '/topic/VirtualTopic.eng.freshmaker.event.state.changed':
            self.event_state_handler(msg)
        elif topic == '/topic/VirtualTopic.eng.freshmaker.build.state.changed':
            self.build_state_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def event_state_handler(self, msg):
        """
        Handle a Freshmaker event state changed message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        event = FreshmakerEvent.create_or_update({
            'id_': msg['body']['msg']['id'],
            'event_type_id': msg['body']['msg']['event_type_id'],
            'message_id': msg['body']['msg']['message_id'],
            'state': msg['body']['msg']['state'],
            'state_name': msg['body']['msg']['state_name'],
            'state_reason': msg['body']['msg']['state_reason'],
            'url': msg['body']['msg']['url']
        })[0]

        advisory = Advisory.get_or_create({
            'id_': msg['body']['msg']['search_key']
        })[0]

        event.conditional_connect(event.triggered_by_advisory, advisory)

        builds = msg['body']['msg']['builds']
        event_id = msg['body']['msg']['id']

        for build in builds:
            koji_build = self.create_or_update_build(build, event_id)
            if koji_build:
                event.triggered_container_builds.connect(koji_build)

    def build_state_handler(self, msg):
        """
        Handle a Freshmaker build state changed message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        build = msg['body']['msg']
        event_id = msg['body']['msg']['id']
        self.create_or_update_build(build, event_id)

    def create_or_update_build(self, build, event_id):
        """
        Use the Koji Task Result to create or update a ContainerKojiBuild.

        :param dict build: the build being created or updated
        :param int event_id: the id of the Freshmaker event
        :return: the created/updated ContainerKojiBuild or None if it cannot be created
        :rtype: ContainerKojiBuild or None
        """
        if not build['build_id']:
            log.debug('Skipping build update for event {0} because no build ID exists.'.format(
                event_id))
            return None
        try:
            koji_task_result = self.koji_session.getTaskResult(build['build_id'])
        except Exception as error:
            log.warning('Failed to get the Koji task result with ID {0}'.format(build['build_id']))
            log.exception(error)
            return None
        koji_build_id = koji_task_result['koji_builds'][0]
        build_params = {
            'id_': koji_build_id,
            'original_nvr': build['original_nvr']
        }
        if build['state'] in self.freshmaker_to_koji_states:
            build_params['state'] = self.freshmaker_to_koji_states[build['state']]
        else:
            log.warning('Encounted an unknown Freshmaker build state of: {0}'.format(
                build_params['state']))
        try:
            build = ContainerKojiBuild.create_or_update(build_params)[0]
        except neomodel.exceptions.ConstraintValidationFailed:
            build = KojiBuild.nodes.get_or_none(id_=koji_build_id)
            if not build:
                raise
            build.add_label(ContainerKojiBuild.__label__)
            build = ContainerKojiBuild.get_or_create(build_params)[0]
        return build
