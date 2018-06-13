# Estuary Updater

A micro-service that updates the Neo4j graph database used by Estuary in real-time

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

    from __future__ import unicode_literals

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
* Lastly, register your handler by adding the class to `estuary_updater.handlers.all_handlers` such
    as:
    ```python
    from estuary_updater.handlers.distgit import DistGitHandler

    all_handlers = [DistGitHandler, OtherHandlerHere]
    ```
