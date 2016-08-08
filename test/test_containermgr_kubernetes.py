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
Test cases for the commissaire.oscmd module.
"""

from mock import MagicMock

from . import TestCase
from commissaire.compat.urlparser import urlparse
from commissaire.containermgr.kubernetes import KubeContainerManager

CONFIG = {
    'protocol': 'http',
    'host': '127.0.0.1',
    'port': '8080',
    'token': 'token'
}


class Test_KubeContainerManager(TestCase):
    """
    Tests for the KubeContainerManager class.
    """

    def test_node_registered(self):
        """
        Verify that KubeContainerManager().node_registered() works as expected.
        """
        kube_container_mgr = KubeContainerManager(CONFIG)
        # First call should return True. The rest should be False.
        kube_container_mgr.con = MagicMock()
        kube_container_mgr.con.get = MagicMock(side_effect=(
            MagicMock(status_code=200),
            MagicMock(status_code=404),
            MagicMock(status_code=500)))

        self.assertTrue(kube_container_mgr.node_registered('test'))
        self.assertFalse(kube_container_mgr.node_registered('test'))
        self.assertFalse(kube_container_mgr.node_registered('test'))

    def test_get_host_status(self):
        """
        Verify that KuberContainerManager().test_get_host_status() works as expected.
        """
        kube_container_mgr = KubeContainerManager(CONFIG)
        status_struct = {'status': {'use': 'kube'}}
        for test_data in (
                (200, status_struct, False),
                (200, status_struct['status'], True)):
            kube_container_mgr.con.get = MagicMock(return_value=MagicMock(
                status_code=test_data[0],
                json=MagicMock(return_value=test_data[1])))
            status_code, data = kube_container_mgr.get_host_status('10.2.0.2')
            self.assertEquals(test_data[0], status_code)
            self.assertEquals(test_data[1], data)
