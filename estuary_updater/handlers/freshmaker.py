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

    @staticmethod
    def can_handle(msg):
        """
        Determine if the message is a Freshmaker-related message and can be handled by this handler.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        return msg['topic'] == '/topic/VirtualTopic.eng.freshmaker.event.state.changed'

    def handle(self, msg):
        """
        Handle a Freshmaker message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        event = FreshmakerEvent.create_or_update(dict(
            id_=msg['body']['msg']['id'],
            event_type_id=msg['body']['msg']['event_type_id'],
            message_id=msg['body']['msg']['message_id'],
            state=msg['body']['msg']['state'],
            state_name=msg['body']['msg']['state_name'],
            url=msg['body']['msg']['url']
        ))[0]

        advisory = Advisory.get_or_create(dict(
            id_=msg['body']['msg']['search_key']
        ))[0]

        event.conditional_connect(event.triggered_by_advisory, advisory)

        koji_session = koji.ClientSession(self.config['estuary_updater.koji_url'])
        builds = msg['body']['msg']['builds']

        for build in builds:
            try:
                koji_task_result = koji_session.getTaskResult(build['build_id'])
            except Exception as error:
                log.warning("Failed to get the TaskResult with ID {0}".format(build['build_id']))
                log.exception(error)
                continue
            koji_build_id = koji_task_result['koji_builds'][0]
            build_params = {
                'id_': koji_build_id,
                'original_nvr': build['original_nvr']
            }
            try:
                build = ContainerKojiBuild.create_or_update(build_params)[0]
            except neomodel.exceptions.ConstraintValidationFailed:
                build = KojiBuild.nodes.get_or_none(id_=koji_build_id)
                if not build:
                    raise
                build.add_label(ContainerKojiBuild.__label__)
                build = ContainerKojiBuild.get_or_create(build_params)[0]

            event.triggered_container_builds.connect(build)
