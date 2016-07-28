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
Test cases for the commissaire.store.etcdstorehandler.EtcdStoreHandler class.
"""

from . test_store_handler_base_class import _Test_StoreHandler

from commissaire.handlers.models import Status, Host
from commissaire.store.etcdstorehandler import EtcdStoreHandler


class Test_StoreHandlerBaseClass(_Test_StoreHandler):
    """
    Tests for the StoreHandlerBase class.
    """

    cls = EtcdStoreHandler

    def test__format_key_with_no_primary_key(self):
        """
        Verify etcd keys are generated correctly whithout a primary key.
        """
        self.assertEquals(
            '/commissaire/status',
            self.instance._format_key(
                Status.new()))

    def test__format_key_with_primary_key(self):
        """
        Verify etcd keys are generated correctly whith a primary key.
        """
        self.assertEquals(
            '/commissaire/hosts/10.0.0.1',
            self.instance._format_key(
                Host.new(
                    address='10.0.0.1', status='', os='', cpus=2,
                    memory=1024, space=1000, last_check='',
                    ssh_priv_key='', remote_user='')))
