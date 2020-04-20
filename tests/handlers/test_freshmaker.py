# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import json
from os import path
from datetime import datetime

from estuary.models.freshmaker import FreshmakerEvent, FreshmakerBuild
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
    assert event.time_created == datetime(2019, 8, 21, 13, 42, 20, tzinfo=pytz.utc)
    assert event.time_done is None

    advisory = Advisory.nodes.get_or_none(id_='34625')
    assert advisory is not None
    assert advisory.advisory_name == 'RHBA-8018:0593-01'
    assert event.triggered_by_advisory.is_connected(advisory)
    # No container builds should be attached since the builds in Koji only exist after the
    # build task Freshmaker tracks is complete
    assert len(event.successful_koji_builds) == 0


def test_event_to_complete(cb_one):
    """Test the Freshmaker handler when it receives an event to complete message."""
    advisory = Advisory.get_or_create({
        'id_': '34727',
        'advisory_name': 'RHBA-8018:0600-01'
    })[0]
    event = FreshmakerEvent.get_or_create({
        'id_': '2194',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id':
            'ID:messaging.domain.com-42045-1527890187852-9:1045742:0:0:1.RHBA-8018:0600-01'
    })[0]
    event.successful_koji_builds.connect(cb_one)
    event.triggered_by_advisory.connect(advisory)
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
    assert event.time_created == datetime(2019, 8, 21, 13, 42, 20, tzinfo=pytz.utc)
    assert event.time_done == datetime(2099, 8, 21, 13, 42, 20, tzinfo=pytz.utc)
    assert len(event.successful_koji_builds) == 1


@mock.patch('koji.ClientSession')
def test_build_state_change(mock_koji_cs, mock_getBuild_one):
    """Test the Freshmaker handler when it receives a build state change message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getTaskResult.return_value = {'koji_builds': ['710916']}
    mock_koji_session.getBuild.return_value = mock_getBuild_one
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '2094',
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
    assert build.id_ == '710916'
    assert build.name == 'e2e-container-test-product-container'
    assert build.original_nvr == 'e2e-container-test-product-container-7.5-133'
    assert build.release == '36.1528968216'
    assert build.version == '7.4'
    assert build.start_time == datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc)
    assert build.state == 1
    assert build.triggered_by_freshmaker_event.is_connected(event)

    assert event.successful_koji_builds.is_connected(build)
    assert len(event.successful_koji_builds) == 1

    mock_koji_session.getTaskResult.assert_called_once_with(16735050)
    mock_koji_session.getBuild.assert_called_once_with(710916, strict=True)

    freshmaker_build = FreshmakerBuild.nodes.get_or_none(id_='1260')
    assert freshmaker_build is not None
    assert freshmaker_build.id_ == '1260'
    assert freshmaker_build.build_id == 16735050
    assert freshmaker_build.name == 'e2e-container-test-product-container'
    assert freshmaker_build.original_nvr == 'e2e-container-test-product-container-7.5-133'
    assert freshmaker_build.rebuilt_nvr == 'e2e-container-test-product-container-7.4-36.1528968216'
    assert freshmaker_build.state == 1
    assert freshmaker_build.state_name == 'DONE'
    assert freshmaker_build.state_reason == 'Built successfully.'
    assert freshmaker_build.time_submitted == datetime(2018, 6, 14, 20, 26, 6, tzinfo=pytz.utc)
    assert freshmaker_build.type_ == 1
    assert freshmaker_build.type_name == 'IMAGE'
    assert freshmaker_build.url == 'http://freshmaker.domain.com/api/1/builds/1260'
    assert event.requested_builds.is_connected(freshmaker_build)
