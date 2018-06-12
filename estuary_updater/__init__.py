# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals

import logging
import pkg_resources

import fedmsg.config


config = fedmsg.config.load_config()
log = logging.getLogger('EstuaryUpdater')
logging.basicConfig(format='[%(filename)s:%(lineno)s:%(funcName)s] %(message)s',
                    level=config.get('estuary_updater.log_level'))

try:
    version = pkg_resources.get_distribution('estuary').version
except pkg_resources.DistributionNotFound:
    version = 'unknown'
