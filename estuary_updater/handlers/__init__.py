# SPDX-License-Identifier: GPL-3.0+

from __future__ import unicode_literals, absolute_import

from estuary_updater.handlers.freshmaker import FreshmakerHandler
from estuary_updater.handlers.distgit import DistGitHandler
from estuary_updater.handlers.errata import ErrataHandler
from estuary_updater.handlers.koji import KojiHandler


# All handler classes are added here
all_handlers = [DistGitHandler, FreshmakerHandler, ErrataHandler, KojiHandler]
