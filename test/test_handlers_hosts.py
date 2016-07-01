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
Test cases for the commissaire.handlers.hosts module.
"""

import mock

import falcon

from . import TestCase
from .constants import *
from commissaire.handlers import hosts
from commissaire.handlers.models import Hosts, Host, Cluster
from commissaire.middleware import JSONify
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_Hosts(TestCase):
    """
    Tests for the Hosts model.
    """

    def test_hosts_creation(self):
        """
        Verify Hosts model.
        """
        # Make sure hosts is required
        self.assertRaises(
            TypeError,
            hosts.Hosts
        )

        # Make sure an empty Hosts is still valid
        hosts_model = hosts.Hosts(hosts=[])
        self.assertEquals(
            '[]',
            hosts_model.to_json())

        # Make sure a Host is accepted as expected
        hosts_model = make_new(HOSTS)
        self.assertEquals(1, len(hosts_model.hosts))
        self.assertEquals(type(str()), type(hosts_model.to_json()))

        # Make sure other instances are not accepted
        hosts_model = hosts.Hosts(hosts=[object()])


class Test_HostCredsResource(TestCase):
    """
    Tests for the HostCreds Resource.
    """

    def before(self):
        self.api = falcon.API(middleware = [JSONify()])
        self.resource = hosts.HostCredsResource()
        self.api.add_route('/api/v0/host/{address}/creds', self.resource)

    def test_host_creds_retrieve(self):
        """
        Verify retrieving Host Credentials.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify if the host exists the data is returned
            manager.get.return_value = make_new(HOST)

            body = self.simulate_request('/api/v0/host/10.2.0.2/creds')
            # datasource's get should have been called once
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(
                json.loads(HOST_CREDS_JSON),
                json.loads(body[0]))

            # Verify no host returns the proper result
            manager.reset_mock()
            manager.get.side_effect = Exception

            body = self.simulate_request('/api/v0/host/10.9.9.9/creds')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual({}, json.loads(body[0]))

class Test_HostsResource(TestCase):
    """
    Tests for the Hosts Resource.
    """

    def before(self):
        self.api = falcon.API(middleware = [JSONify()])
        self.resource = hosts.HostsResource()
        self.api.add_route('/api/v0/hosts', self.resource)

    def test_hosts_listing(self):
        """
        Verify listing Hosts.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]
            manager.list.return_value = make_new(HOSTS)

            body = self.simulate_request('/api/v0/hosts')
            # datasource's get should have been called once
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(
                [json.loads(HOST_JSON)],
                json.loads(body[0]))

    def test_hosts_listing_with_no_hosts(self):
        """
        Verify listing Hosts when no hosts exists.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = Hosts(hosts=[])
            body = self.simulate_request('/api/v0/hosts')
            # datasource's get should have been called once
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual({}, json.loads(body[0]))

    def test_hosts_listing_with_no_etcd_result(self):
        """
        Verify listing hosts handles no etcd result properly.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], Exception]]
            body = self.simulate_request('/api/v0/hosts')
            # datasource's get should have been called once
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual('{}', body[0])


class Test_Host(TestCase):
    """
    Tests for the Host model.
    """

    def test_host_creation(self):
        """
        Verify host model
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            hosts.Host
        )

        # Make sure a Host creates expected results
        host_model = make_new(HOST)
        self.assertEquals(type(str()), type(host_model.to_json()))


class Test_HostResource(TestCase):
    """
    Tests for the Host Resource.
    """
    # TODO: This test could use some work

    def before(self):
        self.api = falcon.API(middleware = [JSONify()])
        self.resource = hosts.HostResource()
        self.api.add_route('/api/v0/host/{address}', self.resource)

    def test_host_retrieve(self):
        """
        Verify retrieving a Host.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify if the host exists the data is returned
            manager.get.return_value = make_new(HOST)

            body = self.simulate_request('/api/v0/host/10.2.0.2')
            # datasource's get should have been called once
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(
                json.loads(HOST_JSON),
                json.loads(body[0]))

            # Verify no host returns the proper result
            manager.reset_mock()
            manager.get.side_effect = Exception

            body = self.simulate_request('/api/v0/host/10.9.9.9')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual({}, json.loads(body[0]))

    def test_host_delete(self):
        """
        Verify deleting a Host.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify if the host exists the data is returned
            manager.get.return_value = make_new(HOST)

            # Verify deleting of an existing host works
            body = self.simulate_request(
                '/api/v0/host/10.2.0.2', method='DELETE')
            # datasource's delete should have been called once
            self.assertEquals(1, manager.delete.call_count)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual({}, json.loads(body[0]))

            # Verify deleting of a non existing host returns the proper result
            manager.reset_mock()
            manager.delete.side_effect = Exception
            body = self.simulate_request(
                '/api/v0/host/10.9.9.9', method='DELETE')
            self.assertEquals(1, manager.delete.call_count)
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual({}, json.loads(body[0]))

    def test_host_create(self):
        """
        Verify creation of a Host.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            manager.save.return_value = make_new(HOST)
            test_cluster = make_new(CLUSTER)
            manager.get.side_effect = (
                Exception,
                make_new(HOST),
                test_cluster,
                test_cluster)

            data = ('{"ssh_priv_key": "dGVzdAo=", "remote_user": "root",'
                    ' "cluster": "cluster"}')
            body = self.simulate_request(
                '/api/v0/host/10.2.0.1', method='PUT', body=data)
            self.assertEqual(self.srmock.status, falcon.HTTP_201)
            self.assertEqual(json.loads(HOST_JSON), json.loads(body[0]))

            # Make sure creation fails if the cluster doesn't exist
            manager.get.side_effect = Exception

            body = self.simulate_request(
                '/api/v0/host/10.2.0.2', method='PUT', body=data)
            self.assertEqual(self.srmock.status, falcon.HTTP_409)
            self.assertEqual({}, json.loads(body[0]))
            # Make sure creation is idempotent if the request parameters
            # agree with an existing host.
            manager.get.side_effect = (
                make_new(HOST),
                test_cluster)

            body = self.simulate_request(
                '/api/v0/host/10.2.0.1', method='PUT', body=data)
            # datasource's set should not have been called
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(json.loads(HOST_JSON), json.loads(body[0]))

            # Make sure creation fails if the request parameters conflict
            # with an existing host.
            manager.get.side_effect = (
                make_new(HOST),
                make_new(CLUSTER_WITH_HOST))
            bad_data = '{"ssh_priv_key": "boguskey"}'
            body = self.simulate_request(
                '/api/v0/host/10.2.0.2', method='PUT', body=bad_data)
            # datasource's set should not have been called once
            self.assertEqual({}, json.loads(body[0]))
            self.assertEqual(self.srmock.status, falcon.HTTP_409)


class Test_ImplicitHostResource(TestCase):
    """
    Tests for the ImplicitHost Resource.
    """

    def before(self):
        self.api = falcon.API(middleware = [JSONify()])
        self.resource = hosts.ImplicitHostResource()
        self.api.add_route('/api/v0/host', self.resource)

    def test_implicit_host_create(self):
        """
        Verify creation of a Host with an implied address.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            manager.save.return_value = make_new(HOST)

            manager.get.side_effect = (
                Exception,
                make_new(HOST),
                make_new(CLUSTER),
                make_new(HOST))
            data = ('{"ssh_priv_key": "dGVzdAo=", "remote_user": "root",'
                    ' "cluster": "cluster"}')
            body = self.simulate_request(
                '/api/v0/host', method='PUT', body=data)
            self.assertEqual(self.srmock.status, falcon.HTTP_201)
            self.assertEqual(json.loads(HOST_JSON), json.loads(body[0]))

            # Make sure creation fails if the cluster doesn't exist
            manager.get.side_effect = (
                make_new(HOST),
                Exception)
            body = self.simulate_request(
                '/api/v0/host', method='PUT', body=data)
            self.assertEqual(self.srmock.status, falcon.HTTP_409)
            self.assertEqual({}, json.loads(body[0]))

            # Make sure creation is idempotent if the request parameters
            # agree with an existing host.
            manager.get.side_effect = (
                make_new(HOST),
                Cluster(
                    name='cluster',
                    status='ok',
                    hostset=["127.0.0.1"]))

            body = self.simulate_request(
                '/api/v0/host', method='PUT', body=data)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual(json.loads(HOST_JSON), json.loads(body[0]))

            # Make sure creation fails if the request parameters conflict
            # with an existing host.
            manager.get.side_effect = (
                make_new(HOST),
                make_new(HOST))
            bad_data = '{"ssh_priv_key": "boguskey"}'
            body = self.simulate_request(
                '/api/v0/host', method='PUT', body=bad_data)
            self.assertEqual(self.srmock.status, falcon.HTTP_409)
            self.assertEqual({}, json.loads(body[0]))
