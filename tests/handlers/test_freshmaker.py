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
def test_event_to_building(mock_koji_cs, mock_build_one, mock_build_two, mock_build_three):
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
    mock_koji_session.getBuild.side_effect = [mock_build_one, mock_build_two, mock_build_three]
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

    build = ContainerKojiBuild.nodes.get_or_none(id_='710916')
    orig_nvr = 'e2e-container-test-product-container-7.5-129'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert build.name == 'e2e-container-test-product-container'
    assert build.release == '36.1528968216'
    assert build.version == '7.4'
    assert event.triggered_container_builds.is_connected(build)
    assert build.state == 0
    build = ContainerKojiBuild.nodes.get_or_none(id_='123456')
    orig_nvr = 'e2e-container-test-product-container-7.3-210.1523551880'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert build.name == 'e2e-container-test-product-container'
    assert build.release == '37.1528968216'
    assert build.version == '8.4'
    assert event.triggered_container_builds.is_connected(build)
    assert build.state == 0
    build = ContainerKojiBuild.nodes.get_or_none(id_='234567')
    orig_nvr = 'e2e-container-test-product-container-7.4-36'
    assert build is not None
    assert build.original_nvr == orig_nvr
    assert build.name == 'e2e-container-test-product-container'
    assert build.release == '38.1528968216'
    assert build.version == '9.4'
    assert event.triggered_container_builds.is_connected(build)
    assert build.state == 0


@mock.patch('koji.ClientSession')
def test_event_to_complete(mock_koji_cs, mock_build_one, mock_build_two, mock_build_three):
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
    mock_build_one['state'] = 3
    mock_build_two['state'] = 3
    mock_build_three['state'] = 1
    mock_koji_session.getBuild.side_effect = [mock_build_one, mock_build_two, mock_build_three]
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '2194',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id':
            'ID:messaging.domain.com-42045-1527890187852-9:1045742:0:0:1.RHBA-8018:0600-01'
    })[0]
    ContainerKojiBuild.get_or_create({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': '{"container_koji_task_id": 17511743}',
        'id_': '710916',
        'name': 'e2e-container-test-product-container',
        'package_name': 'openstack-zaqar-container',
        'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': 3,
        'version': '7.4'
    })[0].triggered_by_freshmaker_event.connect(event)
    ContainerKojiBuild.get_or_create({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': '{"container_koji_task_id": 123456}',
        'id_': '123456',
        'name': 'e2e-container-test-product-container',
        'package_name': 'openstack-zaqar-container',
        'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
        'owner_name': 'emusk',
        'release': '37.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': 3,
        'version': '8.4'
    })[0].triggered_by_freshmaker_event.connect(event)
    ContainerKojiBuild.get_or_create({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': '{"container_koji_task_id": 234567 }',
        'id_': '234567',
        'name': 'e2e-container-test-product-container',
        'package_name': 'openstack-zaqar-container',
        'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
        'owner_name': 'emusk',
        'release': '38.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': 1,
        'version': '9.4'
    })[0].triggered_by_freshmaker_event.connect(event)
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
def test_build_state_change(mock_koji_cs, mock_build_one):
    """Test the Freshmaker handler when it receives a build state change message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getTaskResult.return_value = {'koji_builds': ['710916']}
    mock_build_one['state'] = 1
    mock_koji_session.getBuild.return_value = mock_build_one
    mock_koji_cs.return_value = mock_koji_session
    event = FreshmakerEvent.get_or_create({
        'id_': '2094',
        'state': 1,
        'state_name': 'BUILDING',
        'event_type_id': 8,
        'message_id': 'ID:messaging.domain.com-42045-1527890187852-9:704208:0:0:1.RHBA-8018:0593-01'
    })[0]
    build = ContainerKojiBuild.create_or_update({
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'epoch': 'epoch',
        'extra': '{"container_koji_task_id": 17511743}',
        'id_': '710916',
        'name': 'e2e-container-test-product-container',
        'package_name': 'openstack-zaqar-container',
        'original_nvr': 'e2e-container-test-product-container-7.3-210.1523551880',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': 0,
        'version': '7.4'
    })[0]
    event.triggered_container_builds.connect(build)
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
