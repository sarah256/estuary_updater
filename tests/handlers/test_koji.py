# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import json
from os import path
from datetime import datetime

from estuary.models.koji import KojiBuild, KojiTag
from estuary.models.distgit import DistGitCommit
import pytz
import mock

from tests import message_dir
from estuary_updater.handlers.koji import KojiHandler
from estuary_updater import config


@mock.patch('koji.ClientSession')
def test_build_complete(mock_koji_cs, mock_getBuild_two):
    """Test the Koji handler when it recieves a new build complete message."""
    mock_koji_session = mock.Mock()
    mock_koji_session.getBuild.return_value = mock_getBuild_two
    mock_koji_cs.return_value = mock_koji_session

    with open(path.join(message_dir, 'koji', 'build_complete.json'), 'r') as f:
        msg = json.load(f)
    assert KojiHandler.can_handle(msg) is True
    handler = KojiHandler(config)
    handler.handle(msg)

    build = KojiBuild.nodes.get_or_none(id_='736244')
    assert build is not None
    assert build.completion_time == datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc)
    assert build.creation_time == datetime(2018, 8, 3, 17, 49, 42, tzinfo=pytz.utc)
    assert build.epoch is None
    assert build.extra == ('{"source": {"original_url": "git://pkgs.domain.com/rpms/python-'
                           'attrs?#3be3cb33e6432d8392ac3d9e6edffd990f618432"}}')
    assert build.id_ == '736244'
    assert build.name == 'python-attrs'
    assert build.release == '8.el8+1325+72a36e76'
    assert build.version == '17.4.0'
    assert build.start_time == datetime(2018, 8, 3, 17, 49, 42, tzinfo=pytz.utc)
    assert build.state == 1

    commit = DistGitCommit.nodes.get_or_none(hash_='3be3cb33e6432d8392ac3d9e6edffd990f618432')

    build.commit.is_connected(commit)


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
