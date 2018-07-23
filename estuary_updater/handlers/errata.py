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
            '/topic/VirtualTopic.eng.errata.builds.added'
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
        else:
            raise RuntimeError('This message is unable to be handled: {0}'.format(msg))

    def activity_status_handler(self, msg):
        """
        Handle an Errata tool activity status message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        advisory_id = msg['body']['headers']['errata_id']

        url = '{0}/erratum/{1}'.format(
            self.config['estuary_updater.errata_api_url'].rstrip('/'), advisory_id)
        response = requests.get(url, auth=requests_kerberos.HTTPKerberosAuth())
        advisory_json = response.json()

        advisory_type = msg['body']['headers']['type'].lower()
        advisory_info = advisory_json['errata'][advisory_type]
        # TODO: The way DateTime objects are handled will need to be changed once we stop using the
        # API, as the strings are formatted differently in the message bus messages
        advisory = {
            'advisory_name': msg['body']['msg']['fulladvisory'],
            'content_types': advisory_info['content_types'],
            'id_': advisory_id,
            'product_short_name': msg['body']['msg']['product'],
            'security_impact': advisory_info['security_impact'],
            'security_sla': advisory_info['security_sla'],
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

        bugs = advisory_json['bugs']['bugs']

        for bug in bugs:
            bug = BugzillaBug.get_or_create({'id_': bug['bug']['id']})[0]
            advisory.attached_bugs.connect(bug)

    def builds_added_handler(self, msg):
        """
        Handle an Errata tool activity status message and update Neo4j if necessary.

        :param dict msg: a message to be processed
        """
        self.koji_session = koji.ClientSession(self.config['estuary_updater.koji_url'])

        nvr = msg['body']['headers']['brew_build']

        try:
            koji_build = self.koji_session.getBuild(nvr, strict=True)
        except Exception:
            log.error('Failed to get brew build with NVR {0}'.format(nvr))
            raise

        build_params = {
            'completion_time': koji_build['completion_time'],
            'creation_time': koji_build['creation_time'],
            'epoch': koji_build['epoch'],
            'extra': koji_build['extra'],
            'id_': koji_build['id'],
            'name': koji_build['package_name'],
            'release': koji_build['release'],
            'start_time': koji_build['start_time'],
            'state': koji_build['state'],
            'version': koji_build['version']
        }

        build = KojiBuild.create_or_update(build_params)[0]

        advisory = Advisory.get_or_create({
            'id_': msg['body']['headers']['errata_id']
        })[0]

        advisory.attached_builds.connect(build)

        owner = User.create_or_update({
            'username': koji_build['owner_name'],
            'email': '{0}@redhat.com'.format(koji_build['owner_name'])
        })[0]

        build.owner.connect(owner)
