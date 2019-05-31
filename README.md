[![Docs Status](https://readthedocs.org/projects/estuary-updater/badge/?version=latest)](https://estuary-updater.readthedocs.io/en/latest/?badge=latest)

# Getting Started

## Overview

Estuary Updater is a micro-service that updates the Neo4j graph database used by Estuary in real-time
by reading and processing messages from the UMB.

## Run the Unit Tests

Since the unit tests require a running Neo4j instance, the tests are run in Docker containers using
Docker Compose. The commands required to run the unit tests are abstracted in
`scripts/run-tests.sh`. This script will create the Docker image required to run the tests based
on `docker/Dockerfile-tests`, create a container with Neo4j, create another container to run
the tests based on the built Docker image, run the tests, and then delete the two created
containers.

To install Docker and Docker Compose on Fedora, run:

```bash
$ sudo dnf install docker docker-compose
```

To start Docker, run:

```bash
$ sudo systemctl start docker
```

To run the tests, run:

```bash
$ sudo scripts/run-tests.sh
```

To run just a single test, you can run:

```bash
sudo scripts/run-tests.sh pytest-3 -vvv tests/test_file::test_name
```

## Code Styling

The codebase conforms to the style enforced by `flake8` with the following exceptions:
* The maximum line length allowed is 100 characters instead of 80 characters

In addition to `flake8`, docstrings are also enforced by the plugin `flake8-docstrings` with
the following exemptions:
* D100: Missing docstring in public module
* D104: Missing docstring in public package

The format of the docstrings should be in the Sphynx style such as:

```
Get a node from Neo4j.

:param str resource: a resource name that maps to a neomodel class
:param str uid: the value of the UniqueIdProperty to query with
:return: an object representing the Neo4j node
:rtype: neomodel.StructuredNode
:raises ValidationError: if an invalid resource was requested
```

## Creating a New Handler

* Create a new file in `estuary_updater/handlers` such as `estuary_updater/handlers/distgit.py`.
* At the top of the new file, add the following license header and imports:
    ```python
    # SPDX-License-Identifier: GPL-3.0+

    from __future__ import unicode_literals, absolute_import

    from estuary_updater.handlers.base import BaseHandler
    ```
* Then you can proceed to create your handler in the same file as such:
    ```python
    class DistGitHandler(BaseHandler):
    """A handler for dist-git related messages."""

    @staticmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        # Code goes here to determine if the message can be handled by this handler

    def handle(self, msg):
        """
        Handle a message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        # Code goes here to handle/process the message
    ```
* Then register your handler by adding the class to `estuary_updater.handlers.all_handlers` such
    as:
    ```python
    from estuary_updater.handlers.distgit import DistGitHandler

    all_handlers = [DistGitHandler, OtherHandlerHere]
    ```
* Lastly, add any additional topics to the `fedmsg.d/config.py` file by editing
    the `estuary_updater.topics` value.

## Writing a New Unit Test For Your Handler

* Create a new file to store the JSON message you want to test your handler with. This should be
    stored in `tests/messages` such as `tests/messages/distgit/new_commit.json`.
* Create a new file in `tests/handlers/` such as `tests/handlers/distgit.py`.
* At the top of the new file, add the following license header and imports:
    ```python
    # SPDX-License-Identifier: GPL-3.0+

    from __future__ import unicode_literals, absolute_import

    import json
    from os import path
    ```
* Then you can proceed to create your unit test in the same file as such:
    ```python
    from estuary.models.distgit import DistGitCommit

    from tests import message_dir
    from estuary_updater.handlers.distgit import DistGitHandler
    from estuary_updater import config


    def test_distgit_new_commit():
        """Test the dist-git handler when it recieves a new commit message."""
        # Load the message to pass to the handler
        with open(path.join(message_dir, 'distgit', 'new_commit.json'), 'r') as f:
            msg = json.load(f)
        # Make sure the handler can handle the message
        assert DistGitHandler.can_handle(msg) is True
        # Instantiate the handler
        handler = DistGitHandler(config)
        # Run the handler
        handler.handle(msg)
        # Verify everything looks good in Neo4j
        commit = DistGitCommit.nodes.get_or_none(hash_='some_hash_from_the_message')
        assert commit is not None
        # Do additional checks here
    ```


## Code Documentation
To document new files, please check [here](https://github.com/release-engineering/estuary-updater/tree/master/docs).
