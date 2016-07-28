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
Test cases for the commissaire.handlers.status module.
"""

import json
import mock

import etcd
import falcon

from . import TestCase
from mock import MagicMock
from commissaire.handlers import status
from commissaire.middleware import JSONify
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_Status(TestCase):
    """
    Tests for the Status model.
    """

    def test_status_creation(self):
        """
        Verify Status model.
        """
        # Make sure status has required inputs
        self.assertRaises(
            TypeError,
            status.Status
        )

        # Make sure a Cluster is accepted as expected
        status_model = status.Status(
            etcd={}, investigator={}, watcher={})
        self.assertEquals(type(str()), type(status_model.to_json()))

    def test_status_defaults_values(self):
        """
        Verify Status model fills default values when missing.
        """
        model_instance = status.Status.new()
        self.assertEquals(
            status.Status._attribute_defaults['investigator'],
            model_instance.investigator)
        self.assertEquals(
            status.Status._attribute_defaults['etcd'],
            model_instance.etcd)
        self.assertEquals(
            status.Status._attribute_defaults['watcher'],
            model_instance.watcher)

        # Only set investigator
        investigator_value = {'test': 'value'}
        model_instance = status.Status.new(investigator=investigator_value)
        self.assertEquals(investigator_value, model_instance.investigator)
        self.assertEquals(
            status.Status._attribute_defaults['etcd'],
            model_instance.etcd)

        # Only set etcd
        etcd_value = {'test': 'value'}
        model_instance = status.Status.new(etcd=etcd_value)
        self.assertEquals(
            status.Status._attribute_defaults['investigator'],
            model_instance.investigator)
        self.assertEquals(etcd_value, model_instance.etcd)

        # Only set watcher
        watcher_value = {'test': 'value'}
        model_instance = status.Status.new(watcher=etcd_value)
        self.assertEquals(
            status.Status._attribute_defaults['watcher'],
            model_instance.investigator)
        self.assertEquals(watcher_value, model_instance.watcher)


class Test_StatusResource(TestCase):
    """
    Tests for the Status resource.
    """
    astatus = ('{"etcd": {"status": "OK"}, "investigator": {"status": '
               '"OK", "info": {"size": 1, "in_use": 1, "errors": []}}, '
               '"watcher": {"status": "OK", "info": '
               '{"size": 1, "in_use": 1, "errors": []}}}')

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.return_value = MagicMock(etcd.EtcdResult)
        self.resource = status.StatusResource()
        self.api.add_route('/api/v0/status', self.resource)

    def test_status_retrieve(self):
        """
        Verify retrieving Status.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            child = MagicMock(value='')
            self.return_value._children = [child]
            self.return_value.leaves = self.return_value._children
            manager.get.return_value = self.return_value

            body = self.simulate_request('/api/v0/status')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(
                json.loads(self.astatus),
                json.loads(body[0]))
