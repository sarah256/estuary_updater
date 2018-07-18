# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import json
from os import path
import datetime

from estuary.models.errata import Advisory
import requests
import mock
import pytz

from estuary_updater.handlers.errata import ErrataHandler
from estuary_updater import config
from tests import message_dir


def test_errata():
    """Test the errata handler when it receives a new activity status message."""
    with open(path.join(message_dir, 'errata', 'errata_api.json'), 'r') as f:
        errata_api_msg = json.load(f)
    url = 'https://errata.domain.com/api/v1/erratum/34661'
    with mock.patch('requests.get') as mock_get:
        mock_response = mock.Mock()
        mock_response.json.return_value = errata_api_msg
        mock_get.return_value = mock_response
        requests.get(url).json()
        with open(path.join(message_dir, 'errata', 'activity_status.json'), 'r') as f:
            msg = json.load(f)
        assert ErrataHandler.can_handle(msg) is True
        handler = ErrataHandler(config)
        handler.handle(msg)
        advisory = Advisory.nodes.get_or_none(id_='34661')
        assert advisory is not None

        assert advisory.actual_ship_date is None
        assert advisory.advisory_name == 'RHEA-2018:34661-01'
        assert advisory.content_types == ['rpm']
        assert advisory.created_at == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)
        assert advisory.issue_date == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)
        assert advisory.product_short_name == 'RHEL'
        assert advisory.release_date is None
        assert advisory.security_impact == 'None'
        assert advisory.security_sla is None
        assert advisory.status_time == datetime.datetime(2018, 7, 3, 14, 15, 40, tzinfo=pytz.utc)
        assert advisory.synopsis == 'libvirt-python bug fix and enhancement update'
        assert advisory.update_date == datetime.datetime(2018, 6, 15, 15, 26, 38, tzinfo=pytz.utc)
