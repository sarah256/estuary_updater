# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import json
from os import path
from datetime import datetime

import pytz

from tests import message_dir
from estuary.models.bugzilla import BugzillaBug
from estuary_updater import config
from estuary.models.user import User
from estuary_updater.handlers.bugzilla import BugzillaHandler


def test_bugzilla_bug():
    """Test the Bugzilla handler when it receives a new bug message."""
    with open(path.join(message_dir, 'bugzilla', 'bug_created.json'), 'r') as f:
        msg = json.load(f)

    assert BugzillaHandler.can_handle(msg) is True
    handler = BugzillaHandler(config)
    handler.handle(msg)

    bug = BugzillaBug.nodes.get_or_none(id_='1732519')
    assert bug is not None
    assert bug.id_ == '1732519'
    assert bug.creation_time == datetime(2019, 7, 23, 14, 36, 18, tzinfo=pytz.utc)
    assert bug.modified_time == datetime(2019, 7, 23, 14, 36, 18, tzinfo=pytz.utc)
    assert bug.priority == 'unspecified'
    assert bug.product_name == 'Red Hat Satellite 6'
    assert bug.product_version == '6.5.0'
    assert bug.resolution == ''
    assert bug.severity == 'low'
    assert bug.short_description == 'Adding Manifest file: Menus don\'t match documentation'
    assert bug.status == 'NEW'
    assert bug.target_milestone == 'Unspecified'

    assignee = User.nodes.get_or_none(username='satellite-doc-list')
    qa_contact = User.nodes.get_or_none(username='satellite-doc-list')
    reporter = User.nodes.get_or_none(username='sarah')

    assert bug.assignee.is_connected(assignee)
    assert bug.qa_contact.is_connected(qa_contact)
    assert bug.reporter.is_connected(reporter)
