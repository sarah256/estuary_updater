# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import json
from os import path
import datetime

from estuary.models.errata import Advisory
from estuary.models.koji import KojiBuild
from estuary.models.user import User
import mock
import pytz

from estuary_updater.handlers.errata import ErrataHandler
from estuary_updater import config
from tests import message_dir


def test_activity_status_handler():
    """Test the errata handler when it receives a new activity status message."""
    with open(path.join(message_dir, 'errata', 'api_errata.json'), 'r') as f:
        errata_api_msg = json.load(f)
    with open(path.join(message_dir, 'errata', 'api_product_info.json'), 'r') as f:
        product_info_msg = json.load(f)
    with open(path.join(message_dir, 'errata', 'api_reporter_info.json'), 'r') as f:
        reporter_info_msg = json.load(f)
    with open(path.join(message_dir, 'errata', 'api_assigned_to_info.json'), 'r') as f:
        assigned_to_info_msg = json.load(f)

    with mock.patch('requests.get') as mock_get:
        mock_response_api = mock.Mock()
        mock_response_prod = mock.Mock()
        mock_response_reporter = mock.Mock()
        mock_response_assigned_to = mock.Mock()
        mock_response_api.json.return_value = errata_api_msg
        mock_response_prod.json.return_value = product_info_msg
        mock_response_reporter.json.return_value = reporter_info_msg
        mock_response_assigned_to.json.return_value = assigned_to_info_msg
        mock_get.side_effect = [mock_response_api, mock_response_prod, mock_response_reporter,
                                mock_response_assigned_to]

        with open(path.join(message_dir, 'errata', 'activity_status.json'), 'r') as f:
            msg = json.load(f)
        assert ErrataHandler.can_handle(msg) is True
        handler = ErrataHandler(config)
        handler.handle(msg)
        advisory = Advisory.nodes.get_or_none(id_='34661')
        assert advisory is not None

        reporter = User.nodes.get_or_none(username='dglover')
        assert reporter.email == 'dglover@redhat.com'
        assigned_to = User.nodes.get_or_none(username='emusk')
        assert assigned_to.email == 'emusk@redhat.com'

        assert advisory.reporter.is_connected(reporter)
        assert advisory.assigned_to.is_connected(assigned_to)

        assert advisory.actual_ship_date is None
        assert advisory.advisory_name == 'RHEA-2018:34661-01'
        assert advisory.content_types == ['rpm']
        assert advisory.created_at == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)
        assert advisory.issue_date == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)
        assert advisory.product_name == 'Red Hat Enterprise Linux'
        assert advisory.product_short_name == 'RHEL'
        assert advisory.release_date is None
        assert advisory.security_impact == 'None'
        assert advisory.security_sla is None
        assert advisory.state == 'QE'
        assert advisory.status_time == datetime.datetime(2018, 7, 3, 14, 15, 40, tzinfo=pytz.utc)
        assert advisory.synopsis == 'libvirt-python bug fix and enhancement update'
        assert advisory.update_date == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)


@mock.patch('requests.get')
def test_activity_status_handler_embargoed(mock_get):
    """Test the errata handler when it receives an embargoed activity status message."""
    mock_response_api = mock.Mock()
    mock_response_api.json.return_value = {
        'errata': {
            'rhsa': {
                'content_types': ['rpms'],
                'id': 2345
            }
        }
    }
    mock_get.side_effect = [mock_response_api]

    with open(path.join(message_dir, 'errata', 'activity_status_embargoed.json'), 'r') as f:
        msg = json.load(f)
    assert ErrataHandler.can_handle(msg) is True
    handler = ErrataHandler(config)
    handler.handle(msg)
    advisory = Advisory.nodes.get_or_none(id_='2345')
    assert advisory is not None
    assert advisory.actual_ship_date is None
    assert advisory.advisory_name == 'REDACTED'
    assert advisory.content_types is None
    assert advisory.created_at is None
    assert advisory.issue_date is None
    assert advisory.product_name is None
    assert advisory.product_short_name is None
    assert advisory.release_date is None
    assert advisory.security_impact is None
    assert advisory.security_sla is None
    assert advisory.state is None
    assert advisory.status_time is None
    assert advisory.synopsis is None
    assert advisory.update_date is None


@mock.patch('koji.ClientSession')
def test_builds_added_handler(mock_koji_cs, mock_getBuild_one):
    """Test the Errata handler when it receives a new builds added message."""
    mock_koji_session = mock.Mock()
    mock_getBuild_one['state'] = 1
    mock_koji_session.getBuild.return_value = mock_getBuild_one
    mock_koji_cs.return_value = mock_koji_session

    advisory = Advisory.get_or_create({'id_': '34983'})[0]

    with open(path.join(message_dir, 'errata', 'builds_added.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert ErrataHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = ErrataHandler(config)
    # Run the handler
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='710916')
    owner = User.nodes.get_or_none(username='emusk')
    assert build is not None
    assert build.name == 'e2e-container-test-product-container'
    assert build.version == '7.4'
    assert build.release == '36.1528968216'
    assert build.completion_time == datetime.datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc)
    assert build.creation_time == datetime.datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc)
    assert build.epoch == 'epoch'
    assert build.extra == '{"container_koji_task_id": 17511743}'
    assert build.id_ == '710916'
    assert build.start_time == datetime.datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc)
    assert build.state == 1

    assert advisory.attached_builds.is_connected(build)
    assert build.owner.is_connected(owner)


@mock.patch('koji.ClientSession')
def test_builds_removed_handler(mock_koji_cs, mock_getBuild_one, cb_one):
    """Test the Errata handler when it receives a new builds removed message."""
    mock_koji_session = mock.Mock()
    mock_getBuild_one['state'] = 1
    mock_koji_session.getBuild.return_value = mock_getBuild_one
    mock_koji_cs.return_value = mock_koji_session

    advisory = Advisory.get_or_create({'id_': '34983'})[0]
    advisory.attached_builds.connect(cb_one)

    with open(path.join(message_dir, 'errata', 'builds_removed.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert ErrataHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = ErrataHandler(config)
    # Run the handler
    handler.handle(msg)

    assert advisory is not None
    assert not advisory.attached_builds.is_connected(cb_one)
