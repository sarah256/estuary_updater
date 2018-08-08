# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import json
from os import path
from datetime import datetime

from estuary.models.freshmaker import FreshmakerEvent
from estuary.models.errata import Advisory
from estuary.models.koji import ContainerKojiBuild
import mock
import pytz

from tests import message_dir
from estuary_updater.handlers.freshmaker import FreshmakerHandler
from estuary_updater import config


def test_event_to_building():
    """Test the Freshmaker handler when it receives an event to building message."""
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
    assert event.id_ == '2092'
    assert event.event_type_id == 8
    assert event.message_id == \
        'ID:messaging.domain.com-42045-1527890187852-9:704208:0:0:1.RHBA-8018:0593-01'
    assert event.state == 1
    assert event.state_name == 'BUILDING'
    assert event.state_reason == \
        'Waiting for composes to finish in order to start to schedule base images for rebuild.'

    advisory = Advisory.nodes.get_or_none(id_='34625')
    assert advisory is not None
    assert advisory.advisory_name == 'RHBA-8018:0593-01'
    assert event.triggered_by_advisory.is_connected(advisory)
    # No container builds should be attached since the builds in Koji only exist after the
    # build task Freshmaker tracks is complete
    assert len(event.triggered_container_builds) == 0


def test_event_to_complete(cb_one):
    """Test the Freshmaker handler when it receives an event to complete message."""
    event = FreshmakerEvent.get_or_create({
        'id_': '2194',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id':
            'ID:messaging.domain.com-42045-1527890187852-9:1045742:0:0:1.RHBA-8018:0600-01'
    })[0]
    event.triggered_container_builds.connect(cb_one)
    # Load the message to pass to the handler
    with open(path.join(message_dir, 'freshmaker', 'event_to_complete.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert FreshmakerHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = FreshmakerHandler(config)
    # Run the handler
    handler.handle(msg)

    event = FreshmakerEvent.nodes.get_or_none(id_='2194')
    assert event is not None
    assert event.event_type_id == 8
    assert event.message_id == \
        'ID:messaging.domain.com-42045-1527890187852-9:1045742:0:0:1.RHBA-8018:0600-01'
    assert event.state == 2
    assert event.state_name == 'COMPLETE'
    assert event.state_reason == '2 of 3 container image(s) failed to rebuild.'
    assert len(event.triggered_container_builds) == 1


@mock.patch('koji.ClientSession')
def test_build_state_change(mock_koji_cs, mock_getBuild_one):
    """Test the Freshmaker handler when it receives a build state change message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getTaskResult.return_value = {'koji_builds': ['710916']}
    mock_koji_session.getBuild.return_value = mock_getBuild_one
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '1260',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id': 'ID:messaging.domain.com-42045-1527890187852-9:704208:0:0:1.RHBA-8018:0593-01'
    })[0]
    # Load the message to pass to the handler
    with open(path.join(message_dir, 'freshmaker', 'build_state_change.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert FreshmakerHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = FreshmakerHandler(config)
    # Run the handler
    handler.handle(msg)

    build = ContainerKojiBuild.nodes.get_or_none(id_='710916')
    assert build is not None
    assert build.completion_time == datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc)
    assert build.creation_time == datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc)
    assert build.epoch == 'epoch'
    assert build.extra == '{"container_koji_task_id": 17511743}'
    assert build.id_ == '710916'
    assert build.name == 'e2e-container-test-product-container'
    assert build.original_nvr == 'e2e-container-test-product-container-7.5-133'
    assert build.release == '36.1528968216'
    assert build.version == '7.4'
    assert build.start_time == datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc)
    assert build.state == 1
    assert build.triggered_by_freshmaker_event.is_connected(event)

    assert event.triggered_container_builds.is_connected(build)
    assert len(event.triggered_container_builds) == 1

    mock_koji_session.getTaskResult.assert_called_once_with(16735050)
    mock_koji_session.getBuild.assert_called_once_with(710916, strict=True)
