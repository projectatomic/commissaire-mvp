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
Test cases for the commissaire.store.kubcestorehandler.KubernetesStoreHandler class.
"""

import json
import mock
import requests

from . test_store_handler_base_class import _Test_StoreHandler

from commissaire.handlers.models import Cluster, Host
from commissaire.store.kubestorehandler import KubernetesStoreHandler


class Test_KubernetesStoreHandlerClass(_Test_StoreHandler):
    """
    Tests for the KubernetesStoreHandler class.
    """

    cls = KubernetesStoreHandler

    def before(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        self.instance = self.cls(
            {'server_url': 'http://127.0.0.1:8080'})

    def test__format_kwargs(self):
        """
        Verify keyword arguments get formatted properly.
        """
        model_instance = Cluster.new(name='test')
        annotations = {
            'commissaire-cluster-test-name': 'test',
            'commissaire-cluster-test-status': 'test',
        }
        kwargs = self.instance._format_kwargs(model_instance, annotations)
        self.assertEquals({'name': 'test', 'status': 'test'}, kwargs)

    def test__format_model(self):
        """
        Verify responses from Kubernetes can be turned into models.
        """
        model_instance = Cluster.new(name='test')
        resp_data = {'metadata': {'annotations': {
             'commissaire-cluster-test-name': 'test',
             'commissaire-cluster-test-status': 'test',
        }}}
        result = self.instance._format_model(resp_data, model_instance)
        self.assertEquals('test', result.name)
        self.assertEquals('test', result.status)

    def test__dispatch(self):
        """
        Verify dispatching of operations works properly.
        """
        # Test namespace
        self.instance._save_on_namespace = mock.MagicMock()
        self.instance._dispatch('save', Cluster.new(name='test'))
        self.instance._save_on_namespace.assert_called_once()

        self.instance._get_on_namespace = mock.MagicMock()
        self.instance._dispatch('get', Cluster.new(name='test'))
        self.instance._get_on_namespace.assert_called_once()

        self.instance._delete_on_namespace = mock.MagicMock()
        self.instance._dispatch('delete', Cluster.new(name='test'))
        self.instance._delete_on_namespace.assert_called_once()

        self.instance._list_on_namespace = mock.MagicMock()
        self.instance._dispatch('list', Cluster.new(name='test'))
        self.instance._list_on_namespace.assert_called_once()

        # Test host
        self.instance._save_host = mock.MagicMock()
        self.instance._dispatch('save', Host.new(name='test'))
        self.instance._save_host.assert_called_once()

        self.instance._get_host = mock.MagicMock()
        self.instance._dispatch('get', Host.new(name='test'))
        self.instance._get_host.assert_called_once()

        self.instance._delete_host = mock.MagicMock()
        self.instance._dispatch('delete', Host.new(name='test'))
        self.instance._delete_host.assert_called_once()

        self.instance._list_host = mock.MagicMock()
        self.instance._dispatch('list', Host.new(name='test'))
        self.instance._list_host.assert_called_once()

    def test__get_secret(self):
        """
        Verify secret retrieval works properly.
        """
        response = requests.Response()
        response._content = json.dumps({'data': {'test': 'dGVzdA==\n'}})
        response.status_code = requests.codes.OK
        self.instance._store.get = mock.MagicMock(return_value=response)
        result = self.instance._get_secret('test')
        self.instance._store.get.assert_called_once()
        self.assertEquals({'test': 'test'}, result)

    def test__store_secret_without_a_valid_secret(self):
        """
        Make sure we don't get empty secrets.
        """
        response = requests.Response()
        response._content = json.dumps({})
        response.status_code = requests.codes.NOT_FOUND
        self.instance._store.get = mock.MagicMock(return_value=response)
        self.assertRaises(KeyError, self.instance._get_secret, 'test')
        self.instance._store.get.assert_called_once()

    def test__store_secret(self):
        """
        Verify secret saving works properly.
        """
        self.instance._store.post = mock.MagicMock()
        self.instance._store_secret('test', {'test': 'test'})
        self.instance._store.post.assert_called_once_with(
            self.instance._endpoint + '/namespaces/default/secrets',
            json={
                'apiVersion': 'v1',
                'kind': 'Secret',
                'metadata': {
                    'name': 'test',
                    'type': 'Opaque',
                },
                'data': {'test': 'dGVzdA==\n'},
            })

    def test__delete_secret(self):
        """
        Verify secret deletion works properly.
        """
        self.instance._store.delete = mock.MagicMock()
        self.instance._delete_secret('test')
        self.instance._store.delete.assert_called_once_with(
            'http://127.0.0.1:8080/api/v1/namespaces/default/secrets/test')

    def test__get_on_namespace(self):
        """
        Verify getting data from namespaces works.
        """
        model_instance = Cluster.new(name='test')
        self.instance._store.get = mock.MagicMock()
        self.instance._store.get().json().get().get.return_value = {
            'commissaire-cluster-test-name': 'test',
            'commissaire-cluster-test-status': 'ok',
        }

        self.instance._get_on_namespace(model_instance)
