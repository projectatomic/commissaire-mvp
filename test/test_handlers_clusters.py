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
Test cases for the commissaire.handlers.clusters module.
"""

import json
import mock

import etcd
import falcon

from . import TestCase
from .constants import *
from mock import MagicMock
from commissaire import constants as C
from commissaire.handlers import clusters
from commissaire.handlers.models import Host
from commissaire.middleware import JSONify
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_Clusters(TestCase):
    """
    Tests for the Clusters model.
    """
    # XXX: Based on Test_Hosts

    def test_clusters_creation(self):
        """
        Verify Clusters model.
        """
        # Make sure clusters is required
        self.assertRaises(
            TypeError,
            clusters.Clusters
        )

        # Make sure an empty Clusters is still valid
        clusters_model = clusters.Clusters(clusters=[])
        self.assertEquals(
            '[]',
            clusters_model.to_json())

        # Make sure a Cluster is accepted as expected
        clusters_model = clusters.Clusters(
            clusters=[clusters.Cluster.new(
                name='cluster', status='ok', hostset=[])])
        self.assertEquals(1, len(clusters_model.clusters))
        self.assertEquals(type(str()), type(clusters_model.to_json()))

        # Make sure other instances are not accepted
        clusters_model = clusters.Clusters(clusters=[object()])

    def test_clusters_defaults_values(self):
        """
        Verify Clusters model fills default values when missing.
        """
        model_instance = clusters.Clusters.new()
        self.assertEquals(
            clusters.Clusters._attribute_defaults['clusters'],
            model_instance.clusters)


class Test_ClustersResource(TestCase):
    """
    Tests for the Clusters resource.
    """
    # XXX: Based on Test_HostsResource

    cluster_name = u'development'

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClustersResource()
        self.api.add_route('/api/v0/clusters', self.resource)

    def test_clusters_listing(self):
        """
        Verify listing Clusters.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            return_value = clusters.Clusters(
                clusters=[clusters.Cluster.new(
                    name=self.cluster_name, status='', hostset=[])])
            manager.list.return_value = return_value

            body = self.simulate_request('/api/v0/clusters')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

            self.assertEqual(
                [self.cluster_name],
                json.loads(body[0]))

    def test_clusters_listing_with_no_clusters(self):
        """
        Verify listing Clusters when no clusters exist.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            return_value = clusters.Clusters(clusters=[])
            manager = mock.MagicMock(StoreHandlerManager)
            manager.list.return_value = return_value
            _publish.return_value = [manager]

            body = self.simulate_request('/api/v0/clusters')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertEqual({}, json.loads(body[0]))

    def test_clusters_listing_with_no_etcd_result(self):
        """
        Verify listing Clusters handles no etcd result properly.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], etcd.EtcdKeyNotFound()]]

            body = self.simulate_request('/api/v0/clusters')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)
            self.assertEqual('{}', body[0])


class Test_Cluster(TestCase):
    """
    Tests for the Cluster model.
    """
    # XXX: Based on Test_Host

    def test_cluster_creation(self):
        """
        Verify cluster model.
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            clusters.Cluster)

        # Make sure a Cluster creates expected results
        cluster_model = clusters.Cluster.new(
            name='cluster', status='ok', hostset=[])
        self.assertEquals(type(str()), type(cluster_model.to_json()))
        self.assertIn('total', cluster_model.hosts)
        self.assertIn('available', cluster_model.hosts)
        self.assertIn('unavailable', cluster_model.hosts)
        self.assertEquals('cluster', cluster_model.name)
        self.assertEquals('ok', cluster_model.status)
        self.assertEquals([], cluster_model.hostset)
        self.assertEquals(C.CLUSTER_TYPE_DEFAULT, cluster_model.type)

        # Make sure coercion works
        for attr, spec in cluster_model._attribute_map.items():
            value = getattr(cluster_model, attr)

            # Creating simple wrong values
            caster = str
            if spec['type'] is basestring:
                caster = lambda s: 1
            setattr(cluster_model, attr, caster(value))

        cluster_model._coerce()

        # Validate should be happy with the result
        self.assertIsNone(cluster_model._validate())

    def test_cluster_defaults_values(self):
        """
        Verify Cluster model fills default values when missing.
        """
        model_instance = clusters.Cluster.new()
        self.assertEquals(
            clusters.Cluster._attribute_defaults['name'],
            model_instance.name)
        self.assertEquals(
            clusters.Cluster._attribute_defaults['status'],
            model_instance.status)
        self.assertEquals(
            clusters.Cluster._attribute_defaults['hostset'],
            model_instance.hostset)

        # Set subsets of values.
        for kwargs in (
                {'name': 'test'},
                {'name': 'test', 'status': 'ok'},
                {'name': 'test', 'hostset': ['192.168.152.110']},
                {'status': 'ok'},
                {'status': 'ok', 'hostset': ['192.168.152.110']},
                {'hostset': ['192.168.152.110']}):
            model_instance = clusters.Cluster.new(**kwargs)
            not_done = list(clusters.Cluster._attribute_map.keys())
            for k, v in kwargs.items():
                self.assertEquals(v, getattr(model_instance, k))
                not_done.remove(k)
            for k in not_done:
                self.assertEquals(
                clusters.Cluster._attribute_defaults[k],
                getattr(model_instance, k))


class Test_ClusterResource(TestCase):
    """
    Tests for the Cluster resource.
    """
    # Based on Test_HostResource

    acluster = ('{"name": "development", "status": "ok",'
                ' "hosts": {"total": 1,'
                '           "available": 1,'
                '           "unavailable": 0}}')

    etcd_cluster = '{"name": "development", "status": "ok", "hostset": ["10.2.0.2"]}'
    etcd_host = ('{"address": "10.2.0.2",'
                 ' "ssh_priv_key": "dGVzdAo=", "remote_user": "root",'
                 ' "status": "active", "os": "atomic",'
                 ' "cpus": 2, "memory": 11989228, "space": 487652,'
                 ' "last_check": "2015-12-17T15:48:18.710454",'
                 ' "cluster":"development"}')

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterResource()
        self.api.add_route('/api/v0/cluster/{name}', self.resource)

    def test_cluster_retrieve(self):
        """
        Verify retrieving a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster = make_new(CLUSTER_WITH_HOST)
            # Verify if the cluster exists the data is returned
            manager.get.return_value = test_cluster
            manager.list.return_value = make_new(HOSTS)

            body = self.simulate_request('/api/v0/cluster/development')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)

            self.assertEqual(
                json.loads(test_cluster.to_json_with_hosts()),
                json.loads(body[0]))

            # Verify no cluster returns the proper result
            manager.get.reset_mock()
            manager.get.side_effect = Exception

            body = self.simulate_request('/api/v0/cluster/bogus')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

    def test_cluster_create(self):
        """
        Verify creating a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster = make_new(CLUSTER_WITH_HOST)
            # Verify with creation
            manager.get.side_effect = (
                Exception,
                test_cluster,
                test_cluster,
                test_cluster
            )

            test_body = '{"network": "default"}'

            body = self.simulate_request(
                '/api/v0/cluster/development', method='PUT', body=test_body)
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            self.assertEquals('{}', body[0])

            # Verify with existing cluster
            manager.get.return_value = CLUSTER
            body = self.simulate_request(
                '/api/v0/cluster/development', method='PUT', body=test_body)
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            self.assertEquals('{}', body[0])

    def test_cluster_delete(self):
        """
        Verify deleting a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify with proper deletion
            manager.get.return_value = MagicMock()
            body = self.simulate_request(
                '/api/v0/cluster/development', method='DELETE')
            # Get is called to verify cluster exists
            self.assertEquals(falcon.HTTP_200, self.srmock.status)
            self.assertEquals('{}', body[0])

            # Verify when key doesn't exist
            manager.delete.side_effect = etcd.EtcdKeyNotFound
            body = self.simulate_request(
                '/api/v0/cluster/development', method='DELETE')
            self.assertEquals(falcon.HTTP_404, self.srmock.status)
            self.assertEquals('{}', body[0])


class Test_ClusterRestart(TestCase):
    """
    Tests for the ClusterRestart model.
    """

    def test_cluster_restart_creation(self):
        """
        Verify cluster restart model.
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            clusters.ClusterRestart)

        self.assertEquals(type(str()), type(CLUSTER_RESTART.to_json()))

        # Make sure coercion works
        model_instance = ClusterRestart.new()
        for attr, spec in model_instance._attribute_map.items():
            value = getattr(model_instance, attr)

            # Creating simple wrong values
            caster = str
            if spec['type'] is basestring:
                caster = lambda s: 1
            setattr(model_instance, attr, caster(value))

        model_instance._coerce()

        # Validate should be happy with the result
        self.assertIsNone(model_instance._validate())

    def test_cluster_restart_defaults_values(self):
        """
        Verify ClusterRestart model fills default values when missing.
        """
        model_instance = clusters.ClusterRestart.new()
        for k in model_instance._attribute_map.keys():
            self.assertEquals(
                clusters.ClusterRestart._attribute_defaults[k],
                getattr(model_instance, k))

        # Set subsets of values. Not all inputs are provided but it should
        # be enough to catch issues.
        for kwargs in (
                {'name': 'test'},
                {'name': 'test', 'status': 'ok'},
                {'name': 'test', 'restarted': ['192.168.152.110']},
                {'name': 'test', 'in_process': ['192.168.152.110']},
                {'name': 'test', 'started_at': 'test'},
                {'name': 'test', 'finished_at': 'test'},
                {'status': 'ok'},
                {'status': 'test', 'restarted': ['192.168.152.110']},
                {'status': 'ok', 'started_at': 'test'},
                {'status': 'ok', 'finished_at': 'test'},
                {'restarted': ['192.168.152.110']},
                {'in_process': ['192.168.152.110']}):
            model_instance = clusters.ClusterRestart.new(**kwargs)
            not_done = list(clusters.ClusterRestart._attribute_map.keys())
            for k, v in kwargs.items():
                self.assertEquals(v, getattr(model_instance, k))
                not_done.remove(k)
            for k in not_done:
                self.assertEquals(
                clusters.ClusterRestart._attribute_defaults[k],
                getattr(model_instance, k))


class Test_ClusterRestartResource(TestCase):
    """
    Tests for the ClusterRestart resource.
    """

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterRestartResource()
        self.api.add_route('/api/v0/cluster/{name}/restart', self.resource)

    def test_cluster_restart_retrieve(self):
        """
        Verify retrieving a cluster restart.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster_restart = make_new(CLUSTER_RESTART)

            # Verify if the cluster restart exists the data is returned
            manager.get.return_value = test_cluster_restart
            body = self.simulate_request('/api/v0/cluster/development/restart')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual(json.loads(test_cluster_restart.to_json()), json.loads(body[0]))

            # Verify no cluster restart returns the proper result
            manager.get.side_effect = (
                test_cluster_restart,
                Exception)
            body = self.simulate_request('/api/v0/cluster/development/restart')
            self.assertEqual(falcon.HTTP_204, self.srmock.status)
            self.assertEqual([], body)  # Empty data

    def test_cluster_restart_create(self):
        """
        Verify creating a cluster restart.
        """
        # Process is patched because we don't want to exec the subprocess
        # during unittesting
        with mock.patch('cherrypy.engine.publish') as _publish, \
             mock.patch('commissaire.handlers.clusters.Process'):

            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster = make_new(CLUSTER_WITH_HOST)

            manager.get.side_effect = (
                test_cluster,
                Exception,
                MagicMock(StoreHandlerManager),
                make_new(CLUSTER_RESTART))

            body = self.simulate_request(
                '/api/v0/cluster/development/restart',
                method='PUT')
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            result = json.loads(body[0])
            self.assertEquals('in_process', result['status'])
            self.assertEquals([], result['restarted'])
            self.assertEquals([], result['in_process'])


class Test_ClusterHostsResource(TestCase):
    """
    Tests for the ClusterHosts resource.
    """

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterHostsResource()
        self.api.add_route('/api/v0/cluster/{name}/hosts', self.resource)

    def test_cluster_hosts_retrieve(self):
        """
        Verify retrieving a cluster host list.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify if the cluster exists the host list is returned
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request('/api/v0/cluster/cluster/hosts')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual(
                ['10.2.0.2'],
                json.loads(body[0]))

            # Verify bad cluster name returns the proper result
            manager.get.side_effect = Exception
            body = self.simulate_request('/api/v0/cluster/bogus/hosts')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

    def test_cluster_hosts_overwrite(self):
        """
        Verify overwriting a cluster host list.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify setting host list works with a proper request
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts', method='PUT',
                body='{"old": ["10.2.0.2"], "new": ["10.2.0.2", "10.2.0.3"]}')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad request (KeyError) returns the proper result
            manager.get.side_effect = KeyError
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts', method='PUT',
                body='{"new": ["10.2.0.2", "10.2.0.3"]}')
            self.assertEqual(falcon.HTTP_400, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad request (TypeError) returns the proper result
            manager.get.side_effect = TypeError
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts', method='PUT',
                body='["10.2.0.2", "10.2.0.3"]')
            self.assertEqual(falcon.HTTP_400, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad cluster name returns the proper result
            manager.get.side_effect = Exception
            body = self.simulate_request(
                '/api/v0/cluster/bogus/hosts', method='PUT',
                body='{"old": ["10.2.0.2"], "new": ["10.2.0.2", "10.2.0.3"]}')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify host list conflict returns the proper result
            manager.get.side_effect = None
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts', method='PUT',
                body='{"old": [], "new": ["10.2.0.2", "10.2.0.3"]}')
            self.assertEqual(falcon.HTTP_409, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))


class Test_ClusterSingleHostResource(TestCase):
    """
    Tests for the ClusterSingleHost resource.
    """

    ahostset = '["10.2.0.2"]'

    etcd_cluster = '{"name": "cluster", "status": "ok", "hostset": ["10.2.0.2"]}'

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterSingleHostResource()
        self.api.add_route(
            '/api/v0/cluster/{name}/hosts/{address}', self.resource)

    def test_cluster_host_membership(self):
        """
        Verify host membership in a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify member host returns the proper result
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts/10.2.0.2')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify non-member host returns the proper result
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts/10.9.9.9')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad cluster name returns the proper result
            manager.get.side_effect = Exception
            body = self.simulate_request(
                '/api/v0/cluster/bogus/hosts/10.2.0.2')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

    def test_cluster_host_insert(self):
        """
        Verify insertion of host in a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify inserting host returns the proper result
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request(
                '/api/v0/cluster/developent/hosts/10.2.0.3', method='PUT')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad cluster name returns the proper result
            manager.get.side_effect = Exception
            body = self.simulate_request(
                '/api/v0/cluster/bogus/hosts/10.2.0.3', method='PUT')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

    def test_cluster_host_delete(self):
        """
        Verify deletion of host in a cluster.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            # Verify deleting host returns the proper result
            manager.get.return_value = make_new(CLUSTER_WITH_FLAT_HOST)
            body = self.simulate_request(
                '/api/v0/cluster/development/hosts/10.2.0.2', method='DELETE')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))

            # Verify bad cluster name returns the proper result
            manager.get.side_effect = Exception
            body = self.simulate_request(
                '/api/v0/cluster/bogus/hosts/10.2.0.2', method='DELETE')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)
            self.assertEqual({}, json.loads(body[0]))


class Test_ClusterUpgrade(TestCase):
    """
    Tests for the ClusterUpgrade model.
    """

    def test_cluster_upgrade_creation(self):
        """
        Verify cluster upgrade model.
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            clusters.ClusterUpgrade)

        # Make sure a Cluster Upgrade creates expected results
        cluster_upgrade_model = make_new(CLUSTER_UPGRADE)

        self.assertEquals(type(str()), type(cluster_upgrade_model.to_json()))

        # Make sure coercion works
        model_instance = ClusterUpgrade.new()
        for attr, spec in model_instance._attribute_map.items():
            value = getattr(model_instance, attr)

            # Creating simple wrong values
            caster = str
            if spec['type'] is basestring:
                caster = lambda s: 1
            setattr(model_instance, attr, caster(value))

        model_instance._coerce()

        # Validate should be happy with the result
        self.assertIsNone(model_instance._validate())


    def test_cluster_upgrade_defaults_values(self):
        """
        Verify ClusterUpgrade model fills default values when missing.
        """
        model_instance = clusters.ClusterUpgrade.new()
        for k in model_instance._attribute_map.keys():
            self.assertEquals(
                clusters.ClusterUpgrade._attribute_defaults[k],
                getattr(model_instance, k))

        # Set subsets of values. Not all inputs are provided but it should
        # be enough to catch issues.
        for kwargs in (
                {'name': 'test'},
                {'name': 'test', 'status': 'ok'},
                {'name': 'test', 'upgraded': ['192.168.152.110']},
                {'name': 'test', 'in_process': ['192.168.152.110']},
                {'name': 'test', 'started_at': 'test'},
                {'name': 'test', 'finished_at': 'test'},
                {'status': 'ok'},
                {'status': 'test', 'upgraded': ['192.168.152.110']},
                {'status': 'ok', 'started_at': 'test'},
                {'status': 'ok', 'finished_at': 'test'},
                {'upgraded': ['192.168.152.110']},
                {'in_process': ['192.168.152.110']}):
            model_instance = clusters.ClusterUpgrade.new(**kwargs)
            not_done = list(clusters.ClusterUpgrade._attribute_map.keys())
            for k, v in kwargs.items():
                self.assertEquals(v, getattr(model_instance, k))
                not_done.remove(k)
            for k in not_done:
                self.assertEquals(
                clusters.ClusterUpgrade._attribute_defaults[k],
                getattr(model_instance, k))


class Test_ClusterUpgradeResource(TestCase):
    """
    Tests for the ClusterUpgrade resource.
    """

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterUpgradeResource()
        self.api.add_route('/api/v0/cluster/{name}/upgrade', self.resource)

    def test_cluster_upgrade_retrieve(self):
        """
        Verify retrieving a cluster upgrade.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster_upgrade = make_new(CLUSTER_UPGRADE)
            # Verify if the cluster upgrade exists the data is returned
            manager.get.return_value = test_cluster_upgrade
            body = self.simulate_request('/api/v0/cluster/development/upgrade')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual(json.loads(test_cluster_upgrade.to_json()), json.loads(body[0]))

            # Verify no cluster upgrade returns the proper result
            manager.reset_mock()
            manager.get.side_effect = (
                test_cluster_upgrade,
                Exception)

            body = self.simulate_request('/api/v0/cluster/development/upgrade')
            self.assertEqual(falcon.HTTP_204, self.srmock.status)
            self.assertEqual([], body)  # Empty data

    def test_cluster_upgrade_create(self):
        """
        Verify creating a cluster upgrade.
        """
        # Process is patched because we don't want to exec the subprocess
        # during unittesting
        with mock.patch('cherrypy.engine.publish') as _publish, \
             mock.patch('commissaire.handlers.clusters.Process'):

            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            manager.get.side_effect = (
                make_new(CLUSTER_WITH_FLAT_HOST),
                Exception,
                MagicMock(StoreHandlerManager),
                make_new(CLUSTER_UPGRADE))

            # Verify with creation
            body = self.simulate_request(
                '/api/v0/cluster/development/upgrade', method='PUT')
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            result = json.loads(body[0])
            self.assertEquals('in_process', result['status'])
            self.assertEquals([], result['upgraded'])
            self.assertEquals([], result['in_process'])


class Test_ClusterDeploy(TestCase):
    """
    Tests for the ClusterDeploy model.
    """

    def test_cluster_deploy_creation(self):
        """
        Verify cluster deploy model.
        """
        # Make sure it requires data
        self.assertRaises(
            TypeError,
            clusters.ClusterDeploy)

        # Make sure a Cluster Deploy creates expected results
        cluster_deploy_model = make_new(CLUSTER_DEPLOY)

        self.assertEquals(type(str()), type(cluster_deploy_model.to_json()))

        # Make sure coercion works
        model_instance = ClusterDeploy.new()
        for attr, spec in model_instance._attribute_map.items():
            value = getattr(model_instance, attr)

            # Creating simple wrong values
            caster = str
            if spec['type'] is basestring:
                caster = lambda s: 1
            setattr(model_instance, attr, caster(value))

        model_instance._coerce()

        # Validate should be happy with the result
        self.assertIsNone(model_instance._validate())

    def test_cluster_deploy_defaults_values(self):
        """
        Verify ClusterDeploy model fills default values when missing.
        """
        model_instance = clusters.ClusterDeploy.new()
        for k in model_instance._attribute_map.keys():
            self.assertEquals(
                clusters.ClusterDeploy._attribute_defaults[k],
                getattr(model_instance, k))

        # Set subsets of values. Not all inputs are provided but it should
        # be enough to catch issues.
        for kwargs in (
                {'name': 'test'},
                {'name': 'test', 'status': 'ok'},
                {'name': 'test', 'status': 'ok', 'version': '1.0'},
                {'name': 'test', 'deployed': ['192.168.152.110']},
                {'name': 'test', 'in_process': ['192.168.152.110']},
                {'name': 'test', 'started_at': 'test'},
                {'name': 'test', 'finished_at': 'test'},
                {'status': 'ok'},
                {'status': 'test', 'deployed': ['192.168.152.110'], 'version': '1.0'},
                {'status': 'ok', 'started_at': 'test'},
                {'status': 'ok', 'finished_at': 'test'},
                {'deployed': ['192.168.152.110']},
                {'in_process': ['192.168.152.110']},
                {'version': '1.0'}):
            model_instance = clusters.ClusterDeploy.new(**kwargs)
            not_done = list(clusters.ClusterDeploy._attribute_map.keys())
            for k, v in kwargs.items():
                self.assertEquals(v, getattr(model_instance, k))
                not_done.remove(k)
            for k in not_done:
                self.assertEquals(
                clusters.ClusterDeploy._attribute_defaults[k],
                getattr(model_instance, k))

class Test_ClusterDeployResource(TestCase):
    """
    Tests for the ClusterDeploy resource.
    """

    def before(self):
        self.api = falcon.API(middleware=[JSONify()])
        self.resource = clusters.ClusterDeployResource()
        self.api.add_route('/api/v0/cluster/{name}/deploy', self.resource)

    def test_cluster_deploy_retrieve(self):
        """
        Verify retrieving a cluster deploy.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            test_cluster_deploy = make_new(CLUSTER_DEPLOY)
            # Verify if the cluster deploy exists the data is returned
            manager.get.return_value = test_cluster_deploy
            body = self.simulate_request('/api/v0/cluster/development/deploy')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertEqual(json.loads(test_cluster_deploy.to_json()), json.loads(body[0]))

            # Verify no cluster deploy returns the proper result
            manager.reset_mock()
            manager.get.side_effect = (
                test_cluster_deploy,
                Exception)

            body = self.simulate_request('/api/v0/cluster/development/deploy')
            self.assertEqual(falcon.HTTP_204, self.srmock.status)
            self.assertEqual([], body)  # Empty data

    def test_cluster_deploy_create(self):
        """
        Verify creating a deploy deploy.
        """
        # Process is patched because we don't want to exec the subprocess
        # during unittesting
        with mock.patch('cherrypy.engine.publish') as _publish, \
             mock.patch('commissaire.handlers.clusters.Process'):

            manager = mock.MagicMock(StoreHandlerManager)
            _publish.return_value = [manager]

            manager.get.side_effect = (
                make_new(CLUSTER_WITH_FLAT_HOST),
                Exception,
                MagicMock(StoreHandlerManager),
                make_new(CLUSTER_DEPLOY))

            # Verify with creation
            body = self.simulate_request(
                '/api/v0/cluster/development/deploy',
                method='PUT',
                body=json.dumps({'version': '1.0'}))
            self.assertEquals(falcon.HTTP_201, self.srmock.status)
            result = json.loads(body[0])
            self.assertEquals('in_process', result['status'])
            self.assertEquals([], result['deployed'])
            self.assertEquals([], result['in_process'])
