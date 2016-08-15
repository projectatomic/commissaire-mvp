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
Test cases for the commissaire.handlers.networks module.
"""

import json
import mock

import etcd
import falcon

from . import TestCase
from .constants import *
from mock import MagicMock
from commissaire.handlers import networks
from commissaire.middleware import JSONify
from commissaire.store.storehandlermanager import StoreHandlerManager
from commissaire.store.etcdstorehandler import EtcdStoreHandler


class Test_Networks(TestCase):
    """
    Tests for the Networks model.
    """

    def test_networks_creation(self):
        """
        Verify Networks model.
        """
        # Make sure networks is required
        self.assertRaises(
            TypeError,
            networks.Networks
        )

        # Make sure an empty Networks is still valid
        networks_model = networks.Networks(networks=[])
        self.assertEquals(
            '[]',
            networks_model.to_json())

        # Make sure a Network is accepted as expected
        networks_model = networks.Networks(
            networks=[networks.Network.new(
                name='network', type='flannel_etcd', options={})])
        self.assertEquals(1, len(networks_model.networks))
        self.assertEquals(type(str()), type(networks_model.to_json()))

        # Make sure other instances are not accepted
        networks_model = networks.Networks(networks=[object()])

    def test_networks_defaults_values(self):
        """
        Verify Networks model fills default values when missing.
        """
        model_instance = networks.Networks.new()
        self.assertEquals(
            networks.Networks._attribute_defaults['networks'],
            model_instance.networks)


class Test_NetworksResource(TestCase):
    """
    Tests for the Networks resource.
    """

    network_name = u'default'

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = networks.NetworksResource()
        self.api.add_route('/api/v0/networks', self.resource)

    def test_networks_listing(self):
        """
        Verify listing Networks.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            return_value = networks.Networks(
                networks=[networks.Network.new(name=self.network_name)])
            manager.list.return_value = return_value

            body = self.simulate_request('/api/v0/networks')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

            self.assertEqual(
                [self.network_name],
                json.loads(body[0]))

    def test_networks_listing_with_no_networks(self):
        """
        Verify listing Networks when no networks exist.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            return_value = networks.Networks(networks=[])
            manager = mock.MagicMock(StoreHandlerManager)
            manager.list.return_value = return_value
            _publish.return_value = [manager]

            body = self.simulate_request('/api/v0/networks')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual({}, json.loads(body[0]))

    def test_networks_listing_with_no_etcd_result(self):
        """
        Verify listing Networks handles no etcd result properly.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], etcd.EtcdKeyNotFound()]]

            body = self.simulate_request('/api/v0/networks')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual('{}', body[0])


class Test_Network(TestCase):
    """
    Tests for the Network model.
    """

    def test_network_creation(self):
        """
        Verify network model.
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            networks.Network)

        # Make sure a Network creates expected results
        network_model = networks.Network.new(
            name='network', type='flannel_etcd', options={})
        self.assertEquals(type(str()), type(network_model.to_json()))
        self.assertEquals('network', network_model.name)
        self.assertEquals('flannel_etcd', network_model.type)
        self.assertEquals({}, network_model.options)

        # Make sure coercion works
        network_model.name = 1
        network_model.type = 1

        network_model._coerce()

        # Validate should be happy with the result
        self.assertIsNone(network_model._validate())

    def test_network_defaults_values(self):
        """
        Verify Network model fills default values when missing.
        """
        model_instance = networks.Network.new()
        self.assertEquals(
            networks.Network._attribute_defaults['name'],
            model_instance.name)
        self.assertEquals(
            networks.Network._attribute_defaults['type'],
            model_instance.type)
        self.assertEquals(
            networks.Network._attribute_defaults['options'],
            model_instance.options)

        # Set subsets of values.
        for kwargs in (
                {'name': 'test'},
                {'name': 'test', 'type': 'flannel_etcd'},
                {'name': 'test', 'options': {}},
                {'type': 'flannel_etcd'},
                {'type': 'flannel_etcd', 'options': {'address': '192.168.152.110:8080'}},
                {'options': {'address': '192.168.152.110'}}):
            model_instance = networks.Network.new(**kwargs)
            not_done = list(networks.Network._attribute_map.keys())
            for k, v in kwargs.items():
                self.assertEquals(v, getattr(model_instance, k))
                not_done.remove(k)
            for k in not_done:
                self.assertEquals(
                networks.Network._attribute_defaults[k],
                getattr(model_instance, k))


class Test_NetworkResource(TestCase):
    """
    Tests for the Network resource.
    """

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = networks.NetworkResource()
        self.api.add_route('/api/v0/network/{name}', self.resource)

    def test_network_retrieve(self):
        """
        Verify retrieving a network.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_network = networks.Network.new(name='default')
            # Verify if the network exists the data is returned
            manager.get.return_value = test_network

            body = self.simulate_request('/api/v0/network/default')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)

            self.assertEqual(
                json.loads(test_network.to_json()),
                json.loads(body[0]))

            # Verify no network returns the proper result
            manager.get.reset_mock()
            manager.get.side_effect = Exception

            body = self.simulate_request('/api/v0/network/bogus')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

    def test_network_create(self):
        """
        Verify creating a network.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            manager.list_store_handlers.return_value = [[
                EtcdStoreHandler, None, None]]
            test_network = networks.Network.new(name='default')
            # Verify with creation
            manager.get.side_effect = (
                Exception,
                test_network,
                test_network,
                test_network
            )

            test_body = (
                '{"name": "default", "type": "flannel_etcd", "options": {}}')

            body = self.simulate_request(
                '/api/v0/network/default', method='PUT', body=test_body)
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            result = json.loads(body[0])
            self.assertEquals('default', result['name'])
            self.assertEquals('flannel_etcd', result['type'])
            self.assertEquals({}, result['options'])

            # Verify with existing network
            manager.get.return_value = CLUSTER
            body = self.simulate_request(
                '/api/v0/network/default', method='PUT', body=test_body)
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            self.assertEquals('default', result['name'])
            self.assertEquals('flannel_etcd', result['type'])
            self.assertEquals({}, result['options'])

            # Verify failure with flannel_etcd is requests but there is no
            # etcd backend
            manager.list_store_handlers.return_value = []
            body = self.simulate_request(
                '/api/v0/network/default', method='PUT', body=test_body)
            self.assertEquals(falcon.HTTP_409, self.srmock.status)


    def test_network_delete(self):
        """
        Verify deleting a network.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify with proper deletion
            manager.get.return_value = MagicMock()
            body = self.simulate_request(
                '/api/v0/network/development', method='DELETE')
            # Get is called to verify network exists
            self.assertEquals(falcon.HTTP_200, self.srmock.status)
            self.assertEquals('{}', body[0])

            # Verify when key doesn't exist
            manager.delete.side_effect = etcd.EtcdKeyNotFound
            body = self.simulate_request(
                '/api/v0/network/development', method='DELETE')
            self.assertEquals(falcon.HTTP_404, self.srmock.status)
            self.assertEquals('{}', body[0])
