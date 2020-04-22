# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

from estuary.models.freshmaker import FreshmakerEvent, FreshmakerBuild
from estuary.models.errata import Advisory
from estuary.utils.general import timestamp_to_datetime

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

        if msg['body']['msg'].get('dry_run'):
            return

        event_params = {
            'id_': str(msg['body']['msg']['id']),
            'event_type_id': msg['body']['msg']['event_type_id'],
            'state_name': msg['body']['msg']['state_name'],
            'state_reason': msg['body']['msg']['state_reason']
        }

        if 'time_created' in msg['body']['msg']:
            event_params['time_created'] = timestamp_to_datetime(msg['body']['msg']['time_created'])
        if 'time_done' in msg['body']['msg'] and msg['body']['msg']['time_done'] is not None:
            event_params['time_done'] = timestamp_to_datetime(msg['body']['msg']['time_done'])

        event = FreshmakerEvent.create_or_update(event_params)[0]

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
        freshmaker_build = None
        build = None
        # build_id in Freshmaker is actually the task_id
        if not build_info['build_id']:
            log.debug('Skipping Koji build update for event {0} because build_id is not set'.format(
                event_id))
            freshmaker_build = self.create_or_update_freshmaker_build(build_info, event_id)
        # Ignore Freshmaker dry run mode, indicated by a negative ID
        elif build_info['build_id'] < 0:
            log.debug('Skipping build update for event {0} because it is a dry run'.format(
                event_id))
        else:
            freshmaker_build = self.create_or_update_freshmaker_build(build_info, event_id)
            build = self.create_or_update_build(build_info, event_id)
        event = FreshmakerEvent.nodes.get_or_none(id_=str(event_id))
        if event:
            if build:
                event.successful_koji_builds.connect(build)
            if freshmaker_build:
                freshmaker_build.conditional_connect(freshmaker_build.event, event)
        else:
            log.warning('The Freshmaker event {0} does not exist in Neo4j'.format(event_id))

    def create_or_update_freshmaker_build(self, build, event_id):
        """
        Create or update a FreshmakerBuild.

        :param dict build: the build represented in Freshmaker being created or updated
        :param int event_id: the id of the Freshmaker event
        :return: the created/updated FreshmakerBuild or None if it cannot be created
        :rtype: FreshmakerBuild or None
        """
        log.debug('Creating FreshmakerBuild {0}'.format(build['build_id']))
        fb_params = dict(
            id_=build['id'],
            dep_on=build['dep_on'],
            name=build['name'],
            original_nvr=build['original_nvr'],
            rebuilt_nvr=build['rebuilt_nvr'],
            state_name=build['state_name'],
            state_reason=build['state_reason'],
            time_submitted=timestamp_to_datetime(build['time_submitted']),
            type_=build['type'],
            type_name=build['type_name'],
            url=build['url']
        )
        if build['time_completed']:
            fb_params['time_completed'] = timestamp_to_datetime(
                build['time_completed'])
        if build['build_id']:
            fb_params['build_id'] = build['build_id']

        return FreshmakerBuild.create_or_update(fb_params)[0]

    def create_or_update_build(self, build, event_id):
        """
        Use the Koji Task Result to create or update a ContainerKojiBuild.

        :param dict build: the build represented in Freshmaker being created or updated
        :param int event_id: the id of the Freshmaker event
        :return: the created/updated ContainerKojiBuild or None if it cannot be created
        :rtype: ContainerKojiBuild or None
        """
        # Builds in Koji only exist when the Koji task this Freshmaker build represents completes
        if build['state_name'] != 'DONE':
            log.debug('Skipping build update for event {0} because the build is not complete yet'
                      .format(event_id))
            return None
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
