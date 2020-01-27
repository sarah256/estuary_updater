# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import abc
from datetime import datetime
import json

import neomodel
import koji
from estuary.models.koji import KojiBuild, ContainerKojiBuild, ModuleKojiBuild
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
        pkg = build_info['package_name']
        extra = build_info.get('extra')
        # Checking heuristics for determining if a build is a container build, since currently
        # there is no definitive way to do it.
        if not extra:
            return False

        if extra.get('container_koji_build_id') or extra.get('container_koji_task_id'):
            return True
        elif extra.get('image') and (pkg.endswith('-container') or pkg.endswith('-docker')):
            return True

        return False

    def is_module_build(self, build_info):
        """
        Check whether a Koji build is a module build.

        :param KojiBuild build_info: build info from Koji API
        :return: boolean value indicating whether the build is a module build
        :rtype: bool
        """
        build_extra = build_info.get('extra', {})
        if not build_extra:
            return False

        return bool(build_extra.get('typeinfo', {}).get('module'))

    def get_or_create_build(self, identifier, original_nvr=None, force_container_label=False):
        """
        Get a Koji build from Neo4j, or create it if it does not exist in Neo4j.

        :param str/int identifier: an NVR (str) or build ID (int), or a dict of info from Koji API
        :kwarg str original_nvr: original_nvr property for the ContainerKojiBuild
        :kwarg bool force_container_label: when true, this skips the check to see if the build is a
            container and just creates the build with the ContainerKojiBuild label
        :rtype: KojiBuild
        :return: the Koji Build retrieved or created from Neo4j
        """
        if type(identifier) is dict:
            build_info = identifier
        else:
            try:
                build_info = self.koji_session.getBuild(identifier, strict=True)
            except Exception:
                log.error('Failed to get brew build using the identifier {0}'.format(identifier))
                raise

        build_params = {
            'epoch': build_info['epoch'],
            'id_': str(build_info['id']),
            'name': build_info['package_name'],
            'release': build_info['release'],
            'state': build_info['state'],
            'version': build_info['version']
        }

        if build_info.get('extra'):
            build_params['extra'] = json.dumps(build_info['extra'])

        # To handle the case when a message has a null timestamp
        for time_key in ('completion_time', 'creation_time', 'start_time'):
            # Certain Koji API endpoints omit the *_ts values but have the *_time values, so that's
            # why the *_time values are used
            if build_info[time_key]:
                ts_format = r'%Y-%m-%d %H:%M:%S'
                if len(build_info[time_key].rsplit('.', 1)) == 2:
                    # If there are microseconds, go ahead and parse that too
                    ts_format += r'.%f'
                build_params[time_key] = datetime.strptime(build_info[time_key], ts_format)

        owner = User.create_or_update({
            'username': build_info['owner_name'],
            'email': '{0}@redhat.com'.format(build_info['owner_name'])
        })[0]

        if force_container_label or self.is_container_build(build_info):
            if original_nvr:
                build_params['original_nvr'] = original_nvr
            try:
                build = ContainerKojiBuild.create_or_update(build_params)[0]
            except neomodel.exceptions.ConstraintValidationFailed:
                # This must have errantly been created as a KojiBuild instead of a
                # ContainerKojiBuild, so let's fix that.
                build = KojiBuild.nodes.get_or_none(id_=build_params['id_'])
                if not build:
                    # If there was a constraint validation failure and the build isn't just the
                    # wrong label, then we can't recover.
                    raise
                build.add_label(ContainerKojiBuild.__label__)
                build = ContainerKojiBuild.create_or_update(build_params)[0]
        elif self.is_module_build(build_info):
            module_extra_info = build_info['extra'].get('typeinfo', {}).get('module')
            build_params['context'] = module_extra_info.get('context')
            build_params['mbs_id'] = module_extra_info.get('module_build_service_id')
            build_params['module_name'] = module_extra_info.get('name')
            build_params['module_stream'] = module_extra_info.get('stream')
            build_params['module_version'] = module_extra_info.get('version')
            try:
                build = ModuleKojiBuild.create_or_update(build_params)[0]
            except neomodel.exceptions.ConstraintValidationFailed:
                # This must have errantly been created as a KojiBuild instead of a
                # ModuleKojiBuild, so let's fix that.
                build = KojiBuild.nodes.get_or_none(id_=build_params['id_'])
                if not build:
                    # If there was a constraint validation failure and the build isn't just the
                    # wrong label, then we can't recover.
                    raise
                build.add_label(ModuleKojiBuild.__label__)
                build = ModuleKojiBuild.create_or_update(build_params)[0]
        else:
            build = KojiBuild.create_or_update(build_params)[0]

        build.conditional_connect(build.owner, owner)

        return build
