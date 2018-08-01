# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

from estuary.models.errata import Advisory
from estuary.models.bugzilla import BugzillaBug
from estuary.models.koji import KojiBuild
from estuary.models.user import User
from estuary.utils.general import timestamp_to_datetime
import requests
import requests_kerberos
import koji

from estuary_updater.handlers.base import BaseHandler
from estuary_updater import log


class ErrataHandler(BaseHandler):
    """A handler for dist-git related messages."""

    @staticmethod
    def can_handle(msg):
        """
        Determine if this handler can handle this message.

        :param dict msg: a message to be analyzed
        :return: a bool based on if the handler can handle this kind of message
        :rtype: bool
        """
        supported_topics = [
            '/topic/VirtualTopic.eng.errata.activity.status',
            '/topic/VirtualTopic.eng.errata.builds.added',
            '/topic/VirtualTopic.eng.errata.builds.removed'
        ]
        return msg['topic'] in supported_topics

    def handle(self, msg):
        """
        Handle an Errata tool message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        topic = msg['topic']

        if topic == '/topic/VirtualTopic.eng.errata.activity.status':
            self.activity_status_handler(msg)
        elif topic == '/topic/VirtualTopic.eng.errata.builds.added':
            self.builds_added_handler(msg)
        elif topic == '/topic/VirtualTopic.eng.errata.builds.removed':
            self.builds_removed_handler(msg)
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def activity_status_handler(self, msg):
        """
        Handle an Errata tool activity status message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        advisory_id = msg['body']['headers']['errata_id']

        erratum_url = '{0}/api/v1/erratum/{1}'.format(
            self.config['estuary_updater.errata_url'].rstrip('/'), advisory_id)
        response = requests.get(erratum_url, auth=requests_kerberos.HTTPKerberosAuth(), timeout=10)
        advisory_json = response.json()

        advisory_type = msg['body']['headers']['type'].lower()
        advisory_info = advisory_json['errata'][advisory_type]

        product_url = '{0}/products/{1}.json'.format(
            self.config['estuary_updater.errata_url'].rstrip('/'),
            advisory_info['product_id']
        )
        response = requests.get(product_url, auth=requests_kerberos.HTTPKerberosAuth(), timeout=10)
        product_json = response.json()

        reporter_url = '{0}/api/v1/user/{1}'.format(
            self.config['estuary_updater.errata_url'].rstrip('/'), advisory_info['reporter_id'])
        response = requests.get(reporter_url, auth=requests_kerberos.HTTPKerberosAuth(), timeout=10)
        reporter_json = response.json()

        reporter = User.create_or_update({
            'username': reporter_json['login_name'].split('@')[0],
            'email': reporter_json['email_address']
        })[0]

        assigned_to_url = '{0}/api/v1/user/{1}'.format(
            self.config['estuary_updater.errata_url'].rstrip('/'),
            advisory_info['assigned_to_id'])
        response = requests.get(
            assigned_to_url, auth=requests_kerberos.HTTPKerberosAuth(), timeout=10)
        assigned_to_json = response.json()

        assigned_to = User.create_or_update({
            'username': assigned_to_json['login_name'].split('@')[0],
            'email': assigned_to_json['email_address']
        })[0]

        # TODO: The way DateTime objects are handled will need to be changed once we stop using the
        # API, as the strings are formatted differently in the message bus messages
        advisory = {
            'advisory_name': msg['body']['msg']['fulladvisory'],
            'content_types': advisory_info['content_types'],
            'id_': advisory_id,
            'product_name': product_json['product']['name'],
            'product_short_name': msg['body']['msg']['product'],
            'security_impact': advisory_info['security_impact'],
            'security_sla': advisory_info['security_sla'],
            'state': advisory_info['status'],
            'synopsis': msg['body']['headers']['synopsis']
        }
        for dt in ('actual_ship_date', 'created_at', 'issue_date', 'release_date',
                   'status_updated_at', 'update_date'):
            if advisory_info[dt]:
                if dt == 'status_updated_at':
                    estuary_key = 'status_time'
                else:
                    estuary_key = dt
                advisory[estuary_key] = timestamp_to_datetime(advisory_info[dt])

        advisory = Advisory.create_or_update(advisory)[0]

        advisory.reporter.connect(reporter)
        advisory.assigned_to.connect(assigned_to)

        bugs = advisory_json['bugs']['bugs']

        for bug in bugs:
            bug = BugzillaBug.get_or_create({'id_': bug['bug']['id']})[0]
            advisory.attached_bugs.connect(bug)

    def get_or_create_build(self, msg):
        """
        Get a Koji build from Neo4j, or create it if it does not exist in Neo4j.

        :param dict msg: a message to be processed
        :rtype: KojiBuild
        :return: the Koji Build retrieved or created from Neo4j
        """
        self.koji_session = koji.ClientSession(self.config['estuary_updater.koji_url'])

        nvr = msg['body']['headers']['brew_build']

        try:
            koji_build_info = self.koji_session.getBuild(nvr, strict=True)
        except Exception:
            log.error('Failed to get brew build with NVR {0}'.format(nvr))
            raise

        build_params = {
            'completion_time': koji_build_info['completion_time'],
            'creation_time': koji_build_info['creation_time'],
            'epoch': koji_build_info['epoch'],
            'extra': koji_build_info['extra'],
            'id_': koji_build_info['id'],
            'name': koji_build_info['package_name'],
            'release': koji_build_info['release'],
            'start_time': koji_build_info['start_time'],
            'state': koji_build_info['state'],
            'version': koji_build_info['version']
        }

        owner = User.create_or_update({
            'username': koji_build_info['owner_name'],
            'email': '{0}@redhat.com'.format(koji_build_info['owner_name'])
        })[0]

        koji_build = KojiBuild.create_or_update(build_params)[0]

        koji_build.owner.connect(owner)

        return koji_build

    def builds_added_handler(self, msg):
        """
        Handle an Errata tool builds added message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        advisory = Advisory.get_or_create({
            'id_': msg['body']['headers']['errata_id']
        })[0]

        koji_build = self.get_or_create_build(msg)

        advisory.attached_builds.connect(koji_build)

    def builds_removed_handler(self, msg):
        """
        Handle an Errata tool builds removed message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        advisory = Advisory.get_or_create({
            'id_': msg['body']['headers']['errata_id']
        })[0]

        koji_build = self.get_or_create_build(msg)

        advisory.attached_builds.disconnect(koji_build)
