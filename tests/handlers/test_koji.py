# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import json
from os import path
from datetime import datetime

from estuary.models.koji import ContainerKojiBuild, KojiBuild, KojiTag, ModuleKojiBuild
from estuary.models.distgit import DistGitCommit
import koji
import pytz
import mock

from tests import message_dir, utils
from estuary_updater.handlers.koji import KojiHandler
from estuary_updater import config


@mock.patch('koji.ClientSession')
def test_build_complete(mock_koji_cs, mock_getBuild_complete):
    """Test the Koji handler when it recieves a new build complete message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = mock_getBuild_complete
    mock_koji_cs.return_value = mock_koji_session

    with open(path.join(message_dir, 'koji', 'build_complete.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='736244')
    assert build is not None
    assert build.completion_time == datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc)
    assert build.creation_time == datetime(2018, 8, 3, 17, 49, 42, 735510, tzinfo=pytz.utc)
    assert build.epoch is None
    assert build.extra == ('{"source": {"original_url": "git://pkgs.domain.com/rpms/python-'
                           'attrs?#3be3cb33e6432d8392ac3d9e6edffd990f618432"}}')
    assert build.id_ == '736244'
    assert build.name == 'python-attrs'
    assert build.release == '8.el8+1325+72a36e76'
    assert build.version == '17.4.0'
    assert build.start_time == datetime(2018, 8, 3, 17, 49, 42, 735510, tzinfo=pytz.utc)
    assert build.state == 1

    commit = DistGitCommit.nodes.get_or_none(hash_='3be3cb33e6432d8392ac3d9e6edffd990f618432')

    build.commit.is_connected(commit)


@mock.patch('koji.ClientSession')
def test_modulebuild_complete(mock_koji_cs, mock_getBuild_module_complete,
                              module_build_getTag, mock_getBuild_complete):
    """Test the Koji handler when it recieves a new module build complete message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = mock_getBuild_module_complete
    mock_koji_session.getTag.return_value = module_build_getTag
    # These values are present from the return value of getBuild but not listTaggedRPMS
    del mock_getBuild_complete['completion_ts']
    del mock_getBuild_complete['creation_ts']
    del mock_getBuild_complete['start_ts']
    mock_koji_session.listTaggedRPMS.return_value = [[], [mock_getBuild_complete]]
    mock_koji_cs.return_value = mock_koji_session

    with open(path.join(message_dir, 'koji', 'modulebuild_complete.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = ModuleKojiBuild.nodes.get_or_none(id_='753795')
    # Regular Koji Build attributes
    assert build is not None
    assert build.completion_time == datetime(2018, 8, 17, 16, 54, 17, tzinfo=pytz.utc)
    assert build.creation_time == datetime(2018, 8, 17, 16, 54, 29, 130570, tzinfo=pytz.utc)
    assert build.epoch is None
    assert build.extra == ('{"typeinfo": {"module": {"modulemd_str": "module", "name": "virt",'
                           ' "stream": "rhel", "module_build_service_id": 1648, '
                           '"version": "20180817161005", "context": "9edba152", '
                           '"content_koji_tag": "module-virt-rhel-20180817161005-9edba152"}}}')
    assert build.id_ == '753795'
    assert build.name == 'virt'
    assert build.release == '20180817161005.9edba152'
    assert build.version == 'rhel'
    assert build.start_time == datetime(2018, 8, 17, 16, 10, 29, tzinfo=pytz.utc)
    assert build.state == 1
    # Additional Module Koji Build attributes
    assert build.context == '9edba152'
    assert build.mbs_id == 1648
    assert build.module_name == 'virt'
    assert build.module_stream == 'rhel'
    assert build.module_version == '20180817161005'

    commit = DistGitCommit.nodes.get_or_none(hash_='cf0bd75c564366cc03b882a94cdcb9da0945690a')
    component = KojiBuild.nodes.get_or_none(id_='736244')

    build.commit.is_connected(commit)
    build.components.is_connected(component)


@mock.patch('koji.ClientSession')
def test_build_building(mock_koji_cs):
    """Test the Koji handler when it recieves a new build building message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = \
        utils.mock_getBuild(koji.BUILD_STATES['BUILDING'])
    mock_koji_cs.return_value = mock_koji_session

    with open(path.join(message_dir, 'koji', 'build_building.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='710916')
    assert build is not None
    assert build.state == 0

    commit = DistGitCommit.nodes.get_or_none(hash_='09d40c9bdfd34c5130f8f02e49e059efd33bddf7')
    build.commit.is_connected(commit)


@mock.patch('koji.ClientSession')
def test_build_failed(mock_koji_cs):
    """Test the Koji handler when it recieves a new build failed message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = utils.mock_getBuild(koji.BUILD_STATES['FAILED'])
    mock_koji_cs.return_value = mock_koji_session

    utils.mock_kojiBuild(koji.BUILD_STATES['BUILDING'])

    with open(path.join(message_dir, 'koji', 'build_failed.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='710916')
    assert build is not None
    assert build.state == 3


@mock.patch('koji.ClientSession')
def test_build_canceled(mock_koji_cs):
    """Test the Koji handler when it recieves a new build failed message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = \
        utils.mock_getBuild(koji.BUILD_STATES['CANCELED'])
    mock_koji_cs.return_value = mock_koji_session

    utils.mock_kojiBuild(koji.BUILD_STATES['BUILDING'])

    with open(path.join(message_dir, 'koji', 'build_canceled.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='710916')
    assert build is not None
    assert build.state == 4


@mock.patch('koji.ClientSession')
def test_build_deleted(mock_koji_cs):
    """Test the Koji handler when it recieves a new build failed message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = \
        utils.mock_getBuild(koji.BUILD_STATES['DELETED'])
    mock_koji_cs.return_value = mock_koji_session

    utils.mock_kojiBuild(koji.BUILD_STATES['COMPLETE'])

    with open(path.join(message_dir, 'koji', 'build_deleted.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='710916')
    assert build is not None
    assert build.state == 2


def test_build_tag(kb_one):
    """Test the Koji handler when it recieves a new build tag message."""
    with open(path.join(message_dir, 'koji', 'build_tag.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    tag = KojiTag.nodes.get_or_none(id_=15638)

    assert tag.builds.is_connected(kb_one)


def test_build_untag(kb_one, koji_tag):
    """Test the Koji handler when it recieves a new build untag message."""
    with open(path.join(message_dir, 'koji', 'build_untag.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    assert not koji_tag.builds.is_connected(kb_one)


@mock.patch('koji.ClientSession')
def test_containerbuild_operator(mock_koji_cs, mock_cb_operator):
    """Test Koji handler when it receives a message with a new container build as an operator."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = mock_cb_operator
    mock_koji_cs.return_value = mock_koji_session

    with open(path.join(message_dir, 'koji', 'containerbuild_operator.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = ContainerKojiBuild.nodes.get_or_none(id_='973358')
    assert build.operator is True
    assert build.id_ == '973358'
