# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import json
from os import path

from estuary.models.freshmaker import FreshmakerEvent
from estuary.models.errata import Advisory
from estuary.models.koji import ContainerKojiBuild
import mock

from tests import message_dir
from estuary_updater.handlers.freshmaker import FreshmakerHandler
from estuary_updater import config


@mock.patch('koji.ClientSession')
def test_event_to_building(mock_koji_cs):
    """Test the Freshmaker handler when it receives an event to building message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getTaskResult.side_effect = [
        {
            'koji_builds': ['710916']
        },
        {
            'koji_builds': ['123456']
        },
        {
            'koji_builds': ['234567']
        }
    ]
    mock_koji_cs.return_value = mock_koji_session
    # Load the message to pass to the handler
    with open(path.join(message_dir, 'freshmaker', 'event_to_building.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert FreshmakerHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = FreshmakerHandler(config)
    # Run the handler
    handler.handle(msg)

    event = FreshmakerEvent.nodes.get_or_none(id_='2092')
    assert event is not None

    # Check to see if properties are correct
    assert event.id_ == '2092'
    assert event.event_type_id == 8
    assert event.message_id == ('ID:messaging-devops-broker01.web.prod.ext.phx2.redhat.com-42045-15'
                                '27890187852-9:704208:0:0:1.RHBA-8018:0593-01')
    assert event.state == 1
    assert event.state_name == 'BUILDING'
    assert event.url == 'http://freshmaker.domain.com/api/1/events/2092'

    advisory = Advisory.nodes.get_or_none(id_='34625')
    assert advisory is not None
    assert event.triggered_by_advisory.is_connected(advisory)

    build = ContainerKojiBuild.nodes.get_or_none(id_=710916)
    orig_nvr = 'e2e-container-test-product-container-7.5-129'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert event.triggered_container_builds.is_connected(build)
    build = ContainerKojiBuild.nodes.get_or_none(id_=123456)
    orig_nvr = 'e2e-container-test-product-container-7.3-210.1523551880'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert event.triggered_container_builds.is_connected(build)
    build = ContainerKojiBuild.nodes.get_or_none(id_=234567)
    orig_nvr = 'e2e-container-test-product-container-7.4-36'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert event.triggered_container_builds.is_connected(build)
