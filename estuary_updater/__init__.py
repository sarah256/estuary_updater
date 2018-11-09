# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

import logging
import pkg_resources

import fedmsg.config


config = fedmsg.config.load_config()
logging.basicConfig(
    format='%(asctime)s - %(filename)s:%(lineno)s:%(funcName)s - %(levelname)s: %(message)s')
log = logging.getLogger('estuary_updater')
if isinstance(config.get('estuary_updater.log_level'), int):
    log.setLevel(config['estuary_updater.log_level'])
else:
    log.setLevel(logging.INFO)

try:
    version = pkg_resources.get_distribution('estuary').version
except pkg_resources.DistributionNotFound:
    version = 'unknown'
