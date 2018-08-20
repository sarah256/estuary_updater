# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import re
import json

from estuary.models.koji import KojiBuild, KojiTag, ModuleKojiBuild
from estuary.models.distgit import DistGitCommit

from estuary_updater.handlers.base import BaseHandler
from estuary_updater import log


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
            '/topic/VirtualTopic.eng.brew.build.tag',
            '/topic/VirtualTopic.eng.brew.build.untag'
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        topic = msg['topic']

        if topic == '/topic/VirtualTopic.eng.brew.build.complete':
            self.build_complete_handler(msg)
        elif topic == '/topic/VirtualTopic.eng.brew.build.tag' or \
                topic == '/topic/VirtualTopic.eng.brew.build.untag':
            self.build_tag_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def build_complete_handler(self, msg):
        """
        Handle a build complete message and update Neo4j if necessary.

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

            build.commit.connect(commit)

    def build_tag_handler(self, msg):
        """
        Handle a build tag or untag message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        build = KojiBuild.nodes.get_or_none(id_=msg['body']['msg']['build']['id'])
        # Check to see if we want to process this tag
        if not build:
            return

        if build.__label__ == ModuleKojiBuild.__label__:
            extra_json = json.loads(msg['body']['msg']['info']['extra'])
            module_extra_info = extra_json.get('typeinfo', {}).get('module')
            module_build_tag_name = module_extra_info.get('content_koji_tag')
            if module_build_tag_name:
                try:
                    tag_info = self.koji_session.getTag(module_build_tag_name, strict=True)
                except Exception:
                    log.error('Failed to get tag {0}'.format(module_build_tag_name))
                    raise
                module_build_tag = KojiTag.create_or_update(dict(
                    id_=tag_info[0]['tag_id'],
                    name=module_build_tag_name
                ))[0]
                module_build_tag.module_builds.connect(build)

                for item in tag_info:
                    module_component = KojiBuild.get_or_create(dict(
                        id_=item['build_id']
                    ))[0]
                    build.components.connect(module_component)

        tag = KojiTag.create_or_update({
            'id_': msg['body']['msg']['tag']['id'],
            'name': msg['body']['msg']['tag']['name']
        })[0]

        if msg['topic'] == '/topic/VirtualTopic.eng.brew.build.tag':
            tag.builds.connect(build)
        else:
            tag.builds.disconnect(build)
