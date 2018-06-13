# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals


# TODO: Delete this once there is at least one real test
def test_sample(consumer):
    """Test that TravisCI works."""
    consumer.consume({'msg': {}})
    assert 1 == 1
