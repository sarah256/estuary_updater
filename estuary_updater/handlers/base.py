# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import abc
from datetime import datetime
import json

import neomodel
import koji
from estuary.models.koji import KojiBuild, ContainerKojiBuild
from estuary.models.user import User

from estuary_updater import log


class BaseHandler(object):
    """An abstract base class for handlers to enforce the API."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Initialize the handler.

        :param dict config: the fedmsg configuration
        """
        self._koji_session = None
        self.config = config
        if config.get('estuary_updater.neo4j_url'):
            neomodel.config.DATABASE_URL = config['estuary_updater.neo4j_url']
        else:
            log.warn('The configuration "estuary_updater.neo4j_url" was not set, so the default '
                     'will be used')
            neomodel.config.DATABASE_URL = 'bolt://neo4j:neo4j@localhost:7687'

    @staticmethod
    @abc.abstractmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def handle(self, msg):
        """
        Handle a message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        pass

    @property
    def koji_session(self):
        """
        Get a cached Koji session but initialize the connection first if needed.

        :return: a Koji session object
        :rtype: koji.ClientSession
        """
        if not self._koji_session:
            self._koji_session = koji.ClientSession(self.config['estuary_updater.koji_url'])
        return self._koji_session

    def is_container_build(self, build_info):
        """
        Check whether a Koji build is a container build.

        :param KojiBuild build_info: build info from the Koji API
        :return: boolean value indicating whether the build is a container build
        :rtype: bool
        """
        package_name = build_info['package_name']
        # Checking heuristics for determining if a build is a container build, since currently
        # there is no definitive way to do it.
        if build_info['extra'] and (
                build_info['extra'].get('container_koji_build_id') or
                build_info['extra'].get('container_koji_task_id')):
            return True
        elif build_info['extra'].get('image') and\
                (package_name.endswith('-container') or package_name.endswith('-docker')):
            return True
        else:
            return False

    def get_or_create_build(self, identifier, original_nvr=None, force_container_label=False):
        """
        Get a Koji build from Neo4j, or create it if it does not exist in Neo4j.

        :param str/int identifier: an NVR (str) or build ID (int)
        :kwarg str original_nvr: original_nvr property for the ContainerKojiBuild
        :kwarg bool force_container_label: when true, this skips the check to see if the build is a
        container and just creates the build with the ContainerKojiBuild label
        :rtype: KojiBuild
        :return: the Koji Build retrieved or created from Neo4j
        """
        try:
            koji_build_info = self.koji_session.getBuild(identifier, strict=True)
        except Exception:
            log.error('Failed to get brew build using the identifier {0}'.format(identifier))
            raise

        build_params = {
            'completion_time': datetime.fromtimestamp(int(koji_build_info['completion_ts'])),
            'creation_time': datetime.fromtimestamp(int(koji_build_info['creation_ts'])),
            'epoch': koji_build_info['epoch'],
            'extra': json.dumps(koji_build_info['extra']),
            'id_': str(koji_build_info['id']),
            'name': koji_build_info['package_name'],
            'release': koji_build_info['release'],
            'start_time': datetime.fromtimestamp(int(koji_build_info['start_ts'])),
            'state': koji_build_info['state'],
            'version': koji_build_info['version']
        }

        owner = User.create_or_update({
            'username': koji_build_info['owner_name'],
            'email': '{0}@redhat.com'.format(koji_build_info['owner_name'])
        })[0]

        if force_container_label or self.is_container_build(koji_build_info):
            if original_nvr:
                build_params['original_nvr'] = original_nvr
            koji_build = ContainerKojiBuild.create_or_update(build_params)[0]
        else:
            koji_build = KojiBuild.create_or_update(build_params)[0]

        koji_build.owner.connect(owner)

        return koji_build
