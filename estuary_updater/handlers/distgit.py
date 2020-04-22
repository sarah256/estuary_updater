# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import re

from estuary.models.distgit import DistGitRepo, DistGitCommit
from estuary.models.bugzilla import BugzillaBug
from estuary.models.user import User
from estuary.utils.general import timestamp_to_datetime

from estuary_updater.handlers.base import BaseHandler


class DistGitHandler(BaseHandler):
    """A handler for dist-git related messages."""

    @staticmethod
    def can_handle(msg):
        """
        Determine if this is a dist-git message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        supported_topics = [
            '/topic/VirtualTopic.eng.distgit.commit'
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a dist-git message by sending it to the right handler method and update Neo4j.

        :param dict msg: a message to be processed
        """
        if msg['topic'] == '/topic/VirtualTopic.eng.distgit.commit':
            self.commit_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def commit_handler(self, msg):
        """
        Handle a dist-git commit message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        repo = DistGitRepo.get_or_create({
            'namespace': msg['headers']['namespace'],
            'name': msg['headers']['repo']
        })[0]

        # Get the username from the email if the email is a Red Hat email
        email = msg['headers']['email'].lower()
        if email.endswith('@redhat.com'):
            username = email.split('@redhat.com')[0]
        else:
            username = email

        author = User.create_or_update({
            'username': username,
            'email': email
        })[0]

        commit_message = msg['body']['msg']['message']
        commit = DistGitCommit.create_or_update({
            'hash_': msg['headers']['rev'],
            'log_message': commit_message,
            'author_date': timestamp_to_datetime(msg['body']['msg']['author_date']),
            'commit_date': timestamp_to_datetime(msg['body']['msg']['commit_date'])
        })[0]

        bug_rel_mapping = self.parse_bugzilla_bugs(commit_message)

        for bug_id in bug_rel_mapping['resolves']:
            bug = BugzillaBug.get_or_create({
                'id_': bug_id
            })[0]
            commit.resolved_bugs.connect(bug)

        for bug_id in bug_rel_mapping['related']:
            bug = BugzillaBug.get_or_create({
                'id_': bug_id
            })[0]
            commit.related_bugs.connect(bug)

        for bug_id in bug_rel_mapping['reverted']:
            bug = BugzillaBug.get_or_create({
                'id_': bug_id
            })[0]
            commit.reverted_bugs.connect(bug)

        commit.conditional_connect(commit.author, author)

        repo.contributors.connect(author)
        repo.commits.connect(commit)

    @staticmethod
    def parse_bugzilla_bugs(commit_message):
        """
        Parse the Bugzilla bugs mentioned in a a dist-git commit message.

        :param str commit_message: the dist-git commit message
        :rtype: dict
        :return: a dictionary with the keys resolves, related, reverted with
            values as lists of Bugzilla IDs
        """
        # Look for 'Resolves', 'Related', or 'Reverts' action Bugzilla bugs
        bugzilla_bug_pattern = re.compile(
            r'^(?:(reverted|resolves|related)\: *(.+))', re.IGNORECASE | re.MULTILINE)
        matches = re.findall(bugzilla_bug_pattern, commit_message)

        # Pull out the bug id numbers without their prefixes or whitespace
        bug_ids_pattern = re.compile(r'(?:(?:bug|bz|rhbz)\s*#?|#)\s*(\d+)', re.IGNORECASE)

        bug_rel_mapping = {
            'resolves': [],
            'related': [],
            'reverted': []
        }

        # Populate values of bug relationship type keys to their corresponding bug IDs
        for match in matches:
            rel_type = match[0].lower()
            bug_rel_mapping[rel_type] += list(re.findall(bug_ids_pattern, match[1]))

        return bug_rel_mapping
