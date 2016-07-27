# Copyright (C) 2016  Red Hat, Inc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Test cases for the commissaire.jobs.watcher module.
"""

import datetime
import json
import mock
import os

from . import TestCase
from .constants import CLUSTER, HOST, make_new
from commissaire import constants as C
from commissaire.compat.urlparser import urlparse

from commissaire.jobs.watcher import watcher
from commissaire.handlers.models import Hosts, Clusters
from commissaire.store.storehandlermanager import StoreHandlerManager
from Queue import Queue
from mock import MagicMock


class Test_JobsWatcher(TestCase):
    """
    Tests for the watcher job.
    """

    def test_watcher_failed_to_active(self):
        """
        Verify the watcher.
        """
        with mock.patch('commissaire.transport.ansibleapi.Transport') as _tp:

            _tp().check_host_availability.return_value = (0, {})

            q = Queue()

            test_host = make_new(HOST)
            test_host.last_check = (
                datetime.datetime.now() - datetime.timedelta(days=10)
            ).isoformat()
            test_host.status = 'failed'

            test_cluster = make_new(CLUSTER)
            test_cluster.type = C.CLUSTER_TYPE_KUBERNETES
            test_cluster.hostset = [test_host.address]

            store_manager = MagicMock(StoreHandlerManager)
            store_manager.list.side_effect = (
                Hosts.new(hosts=[test_host]),
                Clusters.new(clusters=[test_cluster]))
            store_manager.get.return_value = test_host

            watcher(q, store_manager, run_once=True)

            self.assertEquals(2, store_manager.list.call_count)
            store_manager.save.assert_called_once()
            self.assertEquals('active', test_host.status)

    def test_watcher_without_a_cluster(self):
        """
        Verify the watcher without a cluster.
        """
        with mock.patch('commissaire.transport.ansibleapi.Transport') as _tp:

            _tp().check_host_availability.return_value = (0, {})

            q = Queue()

            test_host = make_new(HOST)
            test_host.last_check = (
                datetime.datetime.now() - datetime.timedelta(days=10)
            ).isoformat()

            store_manager = MagicMock(StoreHandlerManager)
            store_manager.list.return_value = Hosts.new(hosts=[test_host])
            store_manager.get.return_value = test_host

            watcher(q, store_manager, run_once=True)

            store_manager.list.assert_called_once()
            store_manager.save.assert_called_once()
