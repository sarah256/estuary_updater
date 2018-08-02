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


@mock.patch('koji.ClientSession')
def test_event_to_building(mock_koji_cs, mock_getBuild_one, mock_getBuild_two, mock_getBuild_three):
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
    mock_koji_session.getBuild.side_effect = [
        mock_getBuild_one, mock_getBuild_two, mock_getBuild_three]
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
    assert event.message_id == \
        'ID:messaging.domain.com-42045-1527890187852-9:704208:0:0:1.RHBA-8018:0593-01'
    assert event.state == 1
    assert event.state_name == 'BUILDING'
    assert event.state_reason == \
        'Waiting for composes to finish in order to start to schedule base images for rebuild.'

    advisory = Advisory.nodes.get_or_none(id_='34625')
    assert advisory is not None
    assert event.triggered_by_advisory.is_connected(advisory)

    params = (
        {
            'id_': '710916',
            'original_nvr': 'e2e-container-test-product-container-7.5-129',
            'release': '36.1528968216',
            'version': '7.4'
        },
        {
            'id_': '123456',
            'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
            'release': '37.1528968216',
            'version': '8.4'
        },
        {
            'id_': '234567',
            'original_nvr': 'e2e-container-test-product-container-7.4-36',
            'release': '38.1528968216',
            'version': '9.4'
        }
    )
    for param in params:
        build = ContainerKojiBuild.nodes.get_or_none(id_=param['id_'])
        assert build is not None
        assert build.completion_time == datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc)
        assert build.creation_time == datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc)
        assert build.epoch == 'epoch'
        assert build.extra == '{"container_koji_task_id": 17511743}'
        assert build.id_ == param['id_']
        assert build.name == 'e2e-container-test-product-container'
        assert build.original_nvr == param['original_nvr']
        assert build.release == param['release']
        assert build.version == param['version']
        assert build.start_time == datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc)
        assert build.state == 0
        assert event.triggered_container_builds.is_connected(build)


@mock.patch('koji.ClientSession')
def test_event_to_complete(mock_koji_cs, mock_getBuild_one, mock_getBuild_two, mock_getBuild_three,
                           cb_one, cb_two, cb_three):
    """Test the Freshmaker handler when it receives an event to complete message."""
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
    mock_getBuild_one['state'] = 3
    mock_getBuild_two['state'] = 3
    mock_getBuild_three['state'] = 1
    mock_koji_session.getBuild.side_effect = [
        mock_getBuild_one, mock_getBuild_two, mock_getBuild_three]
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '2194',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id':
            'ID:messaging.domain.com-42045-1527890187852-9:1045742:0:0:1.RHBA-8018:0600-01'
    })[0]
    cb_one.triggered_by_freshmaker_event.connect(event)
    cb_two.triggered_by_freshmaker_event.connect(event)
    cb_three.triggered_by_freshmaker_event.connect(event)
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

    build = ContainerKojiBuild.nodes.get_or_none(id_='710916')
    assert build.state == 3
    build = ContainerKojiBuild.nodes.get_or_none(id_='123456')
    assert build.state == 3
    build = ContainerKojiBuild.nodes.get_or_none(id_='234567')
    assert build.state == 1


@mock.patch('koji.ClientSession')
def test_build_state_change(mock_koji_cs, mock_getBuild_one, cb_one):
    """Test the Freshmaker handler when it receives a build state change message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getTaskResult.return_value = {'koji_builds': ['710916']}
    mock_getBuild_one['state'] = 1
    mock_koji_session.getBuild.return_value = mock_getBuild_one
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '2094',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id': 'ID:messaging.domain.com-42045-1527890187852-9:704208:0:0:1.RHBA-8018:0593-01'
    })[0]
    event.triggered_container_builds.connect(cb_one)
    # Load the message to pass to the handler
    with open(path.join(message_dir, 'freshmaker', 'build_state_change.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert FreshmakerHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = FreshmakerHandler(config)
    # Run the handler
    handler.handle(msg)

    assert ContainerKojiBuild.nodes.get_or_none(id_='710916').state == 1
