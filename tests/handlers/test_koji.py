# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import json
from os import path

from estuary.models.koji import KojiBuild

from tests import message_dir
from estuary_updater.handlers.koji import KojiHandler
from estuary_updater import config


def test_koji():
    """Test the dist-git handler when it recieves a new commit message."""
    # Load the message to pass to the handler
    with open(path.join(message_dir, 'distgit', 'new_commit.json'), 'r') as f:
        msg = json.load(f)
    # Make sure the handler can handle the message
    assert KojiHandler.can_handle(msg) is True
    # Instantiate the handler
    handler = KojiHandler(config)
    # Run the handler
    handler.handle(msg)
    # Verify everything looks good in Neo4j
    commit = DistGitCommit.nodes.get_or_none(hash_='some_hash_from_the_message')
    assert commit is not None
    # Do additional checks here