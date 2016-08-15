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
Test cases for the commissaire.jobs.investigator module.
"""

import json
import mock
import os

from . import TestCase
from commissaire.compat.urlparser import urlparse

from commissaire.jobs.investigator import investigator
from commissaire.handlers.models import Host, Cluster
from commissaire.store.storehandlermanager import StoreHandlerManager
from Queue import Queue
from mock import MagicMock


class Test_JobsInvestigator(TestCase):
    """
    Tests for the investigator job.
    """

    etcd_host = ('{"address": "10.2.0.2",'
                 ' "ssh_priv_key": "dGVzdAo=", "remote_user": "root",'
                 ' "status": "available", "os": "atomic",'
                 ' "cpus": 2, "memory": 11989228, "space": 487652,'
                 ' "last_check": "2015-12-17T15:48:18.710454"}')

    def test_investigator(self):
        """
        Verify the investigator.
        """
        with mock.patch('commissaire.transport.ansibleapi.Transport') as _tp:

            _tp().get_info.return_value = (
                0,
                {
                    'os': 'fedora',
                    'cpus': 2,
                    'memory': 11989228,
                    'space': 487652,
                }
            )

            _tp().bootstrap.return_value = (0, {})

            request_queue = Queue()
            response_queue = MagicMock(Queue)

            to_investigate = {
                'address': '10.0.0.2',
                'ssh_priv_key': 'dGVzdAo=',
                'remote_user': 'root'
            }

            manager = MagicMock(StoreHandlerManager)
            manager.get.return_value = Host(**json.loads(self.etcd_host))

            request_queue.put_nowait((
                manager, to_investigate, Cluster.new().__dict__))
            investigator(request_queue, response_queue, run_once=True)

            # Investigator saves *after* bootstrapping.
            self.assertEquals(0, manager.save.call_count)

            self.assertEquals(1, response_queue.put.call_count)
            host, error = response_queue.put.call_args[0][0]
            self.assertEquals(host.status, 'inactive')
            self.assertIsNone(error)
