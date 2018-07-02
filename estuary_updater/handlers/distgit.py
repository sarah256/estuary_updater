# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import re

from estuary.models.distgit import DistGitRepo, DistGitBranch, DistGitCommit
from estuary.models.bugzilla import BugzillaBug
from estuary.models.user import User

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
            '/topic/VirtualTopic.eng.distgit.commit',
            '/topic/VirtualTopic.eng.distgit.push'
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a dist-git message by sending it to the right handler method and update Neo4j.

        :param dict msg: a message to be processed
        """
        if msg['topic'] == '/topic/VirtualTopic.eng.distgit.commit':
            self.commit_handler(msg)
        elif msg['topic'] == '/topic/VirtualTopic.eng.distgit.push':
            self.push_handler(msg)
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

        branch = DistGitBranch.get_or_create({
            'name': msg['headers']['branch'],
            'repo_namespace': msg['headers']['namespace'],
            'repo_name': msg['headers']['repo']
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
            'log_message': commit_message
        })[0]

        # Look for 'Resolves', 'Related', or 'Reverts' action Bugzilla bugs
        bugzilla_bug_pattern = re.compile(
            r'(revert:|resolves:|related:)([rhbz#, \d]+)')
        bugzilla_bugs = re.findall(bugzilla_bug_pattern, commit_message.lower())
        for bugzilla_bug_group in bugzilla_bugs:
            # Each bug group has an action, followed by a string of all of the bugs listed after
            # that action. bug_ids is a list of each bug_id without any prefixes, such as rhbz.
            bug_ids = re.compile(r'(\d+)')
            bug_ids = re.findall(bug_ids, bugzilla_bug_group[1])
            bug_action = bugzilla_bug_group[0]
            for bug_id in bug_ids:
                bug = BugzillaBug.get_or_create({
                    'id_': bug_id
                })[0]
                if bug_action == 'resolves:':
                    commit.resolved_bugs.connect(bug)
                elif bug_action == 'related:':
                    commit.related_bugs.connect(bug)
                elif bug_action == 'reverted:':
                    commit.reverted_bugs.connect(bug)

        commit.conditional_connect(commit.author, author)

        repo.contributors.connect(author)
        repo.branches.connect(branch)
        repo.commits.connect(commit)

        branch.contributors.connect(author)
        branch.commits.connect(commit)

    def push_handler(self, msg):
        """
        Handle dist-git push messages by updating the parent-child relationship of commits in Neo4j.

        :param dict msg: a message to be processed
        """
        commits = msg['body']['msg']['commits']
        parent = DistGitCommit.get_or_create({
            'hash_': msg['body']['msg']['oldrev']
        })[0]
        for commit in commits:
            child = DistGitCommit.get_or_create({
                'hash_': commit
            })[0]
            child.parent.connect(parent)
            parent = child
