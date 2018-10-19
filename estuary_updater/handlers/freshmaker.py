# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

from estuary.models.freshmaker import FreshmakerEvent
from estuary.models.errata import Advisory

from estuary_updater.handlers.base import BaseHandler
from estuary_updater import log


class FreshmakerHandler(BaseHandler):
    """A handler for Freshmaker-related messages."""

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
        msg_id = msg['body']['msg']['message_id']
        event = FreshmakerEvent.create_or_update({
            'id_': str(msg['body']['msg']['id']),
            'event_type_id': msg['body']['msg']['event_type_id'],
            'message_id': msg_id,
            'state': msg['body']['msg']['state'],
            'state_name': msg['body']['msg']['state_name'],
            'state_reason': msg['body']['msg']['state_reason']
        })[0]

        advisory_name = msg_id.rsplit('.', 1)[-1]
        if advisory_name[0:4] not in ('RHSA', 'RHBA', 'RHEA'):
            log.warn('Unable to parse the advisory name from the Freshmaker message_id: {0}'
                     .format(msg_id))
            advisory_name = None
        advisory = Advisory.get_or_create({
            'id_': msg['body']['msg']['search_key'],
            'advisory_name': advisory_name
        })[0]

        event.conditional_connect(event.triggered_by_advisory, advisory)

    def build_state_handler(self, msg):
        """
        Handle a Freshmaker build state changed message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        build_info = msg['body']['msg']
        event_id = msg['body']['msg']['event_id']
        build = self.create_or_update_build(build_info, event_id)
        if build:
            event = FreshmakerEvent.nodes.get_or_none(id_=str(event_id))
            if event:
                event.triggered_container_builds.connect(build)
            else:
                log.warn('The Freshmaker event {0} does not exist in Neo4j'.format(event_id))

    def create_or_update_build(self, build, event_id):
        """
        Use the Koji Task Result to create or update a ContainerKojiBuild.

        :param dict build: the build represented in Freshmaker being created or updated
        :param int event_id: the id of the Freshmaker event
        :return: the created/updated ContainerKojiBuild or None if it cannot be created
        :rtype: ContainerKojiBuild or None
        """
        # Builds in Koji only exist when the Koji task this Freshmaker build represents completes
        if build['state'] != 1:
            log.debug('Skipping build update for event {0} because the build is not complete yet'
                      .format(event_id))
            return None
        # build_id in Freshmaker is actually the task_id
        elif not build['build_id']:
            log.debug('Skipping build update for event {0} because build_id is not set'.format(
                event_id))
            return None
        # Ignore Freshmaker dry run mode, indicated by a negative ID
        elif build['build_id'] < 0:
            log.debug('Skipping build update for event {0} because it is a dry run'.format(
                event_id))
            return

        try:
            koji_task_result = self.koji_session.getTaskResult(build['build_id'])
        except Exception:
            log.error('Failed to get the Koji task result with ID {0}'.format(build['build_id']))
            raise

        if not koji_task_result.get('koji_builds'):
            log.warn('The task result of {0} does not contain the koji_builds key'.format(
                build['build_id']))
            return None
        # The ID is returned as a string so it must be cast to an int
        koji_build_id = int(koji_task_result['koji_builds'][0])
        # It's always going to be a container build when the build comes from Freshmaker, so we can
        # just set force_container_label to avoid unncessary heuristic checks
        return self.get_or_create_build(
            koji_build_id, build['original_nvr'], force_container_label=True)
