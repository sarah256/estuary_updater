# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import re

from estuary.models.distgit import DistGitCommit
from estuary.models.koji import ModuleKojiBuild, ContainerKojiBuild

from estuary_updater.handlers.base import BaseHandler


class KojiHandler(BaseHandler):
    """A handler for Koji related messages."""

    @staticmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        supported_topics = [
            '/topic/VirtualTopic.eng.brew.build.complete',
            '/topic/VirtualTopic.eng.brew.build.building',
            '/topic/VirtualTopic.eng.brew.build.failed',
            '/topic/VirtualTopic.eng.brew.build.canceled',
            '/topic/VirtualTopic.eng.brew.build.deleted',
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        topic = msg['topic']

        build_topic = ['/topic/VirtualTopic.eng.brew.build.complete',
                       '/topic/VirtualTopic.eng.brew.build.building',
                       '/topic/VirtualTopic.eng.brew.build.failed',
                       '/topic/VirtualTopic.eng.brew.build.canceled',
                       '/topic/VirtualTopic.eng.brew.build.deleted']

        if topic in build_topic:
            self.build_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def build_handler(self, msg):
        """
        Handle a build state message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        if not msg['body']['msg']['info']['source']:
            return
        commit_hash_pattern = re.compile(r'(?:\#)([0-9a-f]{40})$')
        commit_hash = re.findall(commit_hash_pattern, msg['body']['msg']['info']['source'])

        # Container builds and rpms have commit hashes, so we want to process them
        if commit_hash:
            commit = DistGitCommit.get_or_create({
                'hash_': commit_hash[0]
            })[0]
            build = self.get_or_create_build(msg['body']['msg']['info']['id'])

            build.conditional_connect(build.commit, commit)

            if build.__label__ == ModuleKojiBuild.__label__:
                extra_json = msg['body']['msg']['info']['extra']
                module_extra_info = extra_json.get('typeinfo', {}).get('module')
                module_build_tag_name = module_extra_info.get('content_koji_tag')
                if module_build_tag_name:
                    _, components = self.koji_session.listTaggedRPMS(module_build_tag_name)
                    for component in components:
                        component_build = self.get_or_create_build(component)
                        build.components.connect(component_build)

            elif build.__label__ == ContainerKojiBuild.__label__:
                extra_json = msg['body']['msg']['info']['extra']
                build.operator = bool(
                    extra_json.get('typeinfo', {}).get('operator-manifests', {}).get('archive')
                )
                build.save()
