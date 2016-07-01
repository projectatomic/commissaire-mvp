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
Test cases for the commissaire.jobs.clusterexec module.
"""

import json
import mock
import cherrypy

from . import TestCase
from .constants import *
from commissaire.jobs.clusterexec import clusterexec
from commissaire.store.storehandlermanager import StoreHandlerManager
from mock import MagicMock



class Test_JobsClusterExec(TestCase):
    """
    Tests for the clusterexec job.
    """

    def test_clusterexec(self):
        """
        Verify the clusterexec.
        """
        for cmd in ('deploy', 'restart', 'upgrade'):
            with mock.patch('commissaire.transport.ansibleapi.Transport') as _tp:

                getattr(_tp(), cmd).return_value = (0, {})

                manager = MagicMock(StoreHandlerManager)
                manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)

                manager.list.return_value = make_new(HOSTS)

                clusterexec(manager, 'cluster', cmd)

                # One for the cluster
                self.assertEquals(1, manager.get.call_count)
                # We should have 4 sets for 1 host
                self.assertEquals(4, manager.save.call_count)

    def test_clusterexec_stops_on_failure(self):
        """
        Verify the clusterexec will stop on first failure.
        """
        for cmd in ('deploy', 'restart', 'upgrade'):
            with mock.patch('cherrypy.engine.publish') as _publish, \
                 mock.patch('commissaire.transport.ansibleapi.Transport') as _tp:

                getattr(_tp(), cmd).return_value = (1, {})

                manager = MagicMock(StoreHandlerManager)
                manager.save.side_effect = (
                    make_new(CLUSTER_WITH_FLAT_HOST),
                    Exception)

                manager.list.return_value = make_new(HOSTS)

                clusterexec(manager, 'default', cmd)

                # One for the cluster
                self.assertEquals(1, manager.get.call_count)
                # We should have 4 sets for 1 host
                self.assertEquals(2, manager.save.call_count)
