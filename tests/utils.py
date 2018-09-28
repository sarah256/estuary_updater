# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

from datetime import datetime

from estuary.models.koji import KojiBuild, ContainerKojiBuild
import koji
import pytz


def mock_getBuild(state=koji.BUILD_STATES['COMPLETE'], is_container=False):
    """
    Make a mock set of build data simulating a Koji getBuild API call.

    :param int state: the state of the build
    :param bool isCommit: true if a commit is connected, false otherwise
    :return: a dictionary with all of the build info
    :rtype: dict
    """
    if state == koji.BUILD_STATES['COMPLETE']:
        completion_time = '2018-06-15 20:26:38.000000'
        completion_ts = 1529094398.0
    else:
        completion_time = None
        completion_ts = None

    if not is_container:
        extra = {
            'source': {
                'original_url': 'git://pkgs.domain.com/rpms/squashfs-tools#09d40c9bdfd34c5130f8f02e'
                                '49e059efd33bddf7'
            }
        }
        name = 'e2e'
    else:
        extra = {'container_koji_task_id': 17511743}
        name = 'e2e-container'

    return {
        'completion_time': completion_time,
        'completion_ts': completion_ts,
        'creation_time': '2018-06-15 20:20:38.000000',
        'creation_ts': 1529094038.0,
        'epoch': 'epoch',
        'extra': extra,
        'id': 710916,
        'name': name,
        'package_name': name,
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'version': '7.4',
        'start_time': '2018-06-15 20:21:38.000000',
        'start_ts': 1529094098.0,
        'state': state
    }


def mock_kojiBuild(state=koji.BUILD_STATES['COMPLETE'], is_container=False):
    """
    Make a mock Koji build.

    :param int state: the state of the build
    :return: a Koji build with mock data
    :rtype: KojiBuild
    """
    build_params = {
        'completion_time': datetime(2018, 6, 15, 20, 26, 38, tzinfo=pytz.utc),
        'creation_time': datetime(2018, 6, 15, 20, 20, 38, tzinfo=pytz.utc),
        'extra': {},
        'id_': '710916',
        'name': 'e2e',
        'owner_name': 'emusk',
        'release': '36.1528968216',
        'start_time': datetime(2018, 6, 15, 20, 21, 38, tzinfo=pytz.utc),
        'state': state,
        'version': '7.4'
    }

    if is_container:
        build_params['extra'] = {'container_koji_task_id': 17511743}
        build_params['name'] = 'e2e-container'
        return ContainerKojiBuild.get_or_create(build_params)[0]
    else:
        build_params['extra'] = {
            'source': {
                'original_url': 'git://pkgs.domain.com/rpms/squashfs-tools#09d'
                                '40c9bdfd34c5130f8f02e49e059efd33bddf7'
            }
        }
        return KojiBuild.get_or_create(build_params)[0]
