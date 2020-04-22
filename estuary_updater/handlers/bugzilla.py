# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

from estuary.utils.general import timestamp_to_datetime
from estuary.models.bugzilla import BugzillaBug
from estuary.models.user import User

from estuary_updater.handlers.base import BaseHandler


class BugzillaHandler(BaseHandler):
    """A handler for Bugzilla bug related messages."""

    @staticmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        supported_topics = [
            '/topic/VirtualTopic.eng.bugzilla.bug.modify',
            '/topic/VirtualTopic.eng.bugzilla.bug.create',
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle a Bugzilla bug message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        if self.can_handle(msg):
            self.bug_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def bug_handler(self, msg):
        """
        Handle a modified or created Bugzilla bug and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        bug_data = msg['body']['msg']['bug']
        bug_params = {
            'id_': str(bug_data['id']),
            'creation_time': timestamp_to_datetime(bug_data['creation_time']),
            'modified_time': timestamp_to_datetime(bug_data['last_change_time']),
            'priority': bug_data['priority'],
            'product_name': bug_data['product']['name'],
            'product_version': bug_data['version']['name'],
            'resolution': bug_data['resolution'],
            'severity': bug_data['severity'],
            'short_description': bug_data['summary'],
            'status': bug_data['status']['name'],
            'target_milestone': bug_data['target_milestone']['name'],
        }
        assignee = User.create_or_update({
            'username': bug_data['assigned_to']['login'].split('@')[0],
            'email': bug_data['assigned_to']['login']
        })[0]
        qa_contact = User.create_or_update({
            'username': bug_data['qa_contact']['login'].split('@')[0],
            'email': bug_data['qa_contact']['login']
        })[0]
        reporter = User.create_or_update({
            'username': bug_data['reporter']['login'].split('@')[0],
            'email': bug_data['reporter']['login']
        })[0]

        bug = BugzillaBug.create_or_update(bug_params)[0]

        bug.conditional_connect(bug.assignee, assignee)
        bug.conditional_connect(bug.qa_contact, qa_contact)
        bug.conditional_connect(bug.reporter, reporter)
