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
Kubernetes based StoreHandler.
"""

import json
import requests

from commissaire.compat.b64 import base64
from commissaire.containermgr.kubernetes import KubeContainerManager
from commissaire.handlers.models import Hosts, Host
from commissaire.store import StoreHandlerBase

_API_VERSION = 'v1'

#: Maps ModelClassName to Kubernetes path
_model_mapper = {
    'Cluster': '/namespaces/default/',
    'ClusterDeploy': '/namespaces/default/',
    'ClusterRestart': '/namespaces/default/',
    'ClusterUpgrade': '/namespaces/default/',
    'Clusters': '/namespaces/default/',
    'Host': '/nodes/',
    'Hosts': '/nodes/',
    'Status': '/namespaces/default/',
}


class KubernetesStoreHandler(StoreHandlerBase):
    """
    Handler for data storage on Kubernetes.
    """

    container_manager_class = KubeContainerManager

    def __init__(self, config):
        """
        Creates a new instance of KubernetesStoreHandler.

        :param config: Configuration details
        :type config: dict
        """
        self._store = requests.Session()
        # Use a bearer token if it's provided
        token = config.get('token', None)
        if token:
            self._store.headers["Authorization"] = "Bearer {0}".format(token)

        # Use client certificate if it's provided
        certificate_path = config.get('certificate_path')
        certificate_key_path = config.get('certificate_key_path')
        if certificate_path and certificate_key_path:
            self._store.cert = (certificate_path, certificate_key_path)

        # TODO: Verify TLS!!!
        self._store.verify = False
        self._endpoint = '{0}://{1}:{2}/api/{3}'.format(
            config['protocol'], config['host'],
            config['port'], _API_VERSION)

        # The endpoint to hit for secrets
        self._secrets_endpoint = self._endpoint + '/namespaces/default/secrets'

    def _format_kwargs(self, model_instance, annotations, listing=False):
        """
        Formats keyword arguments used when creating a model.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :param annotations: Annotations to use when creating keyword arguments.
        :type annotations: dict
        :param listing: Notes if this is an attempt to get a list of items.
        :type listing: bool
        :returns: Dictionary of keyword arguments
        :rtype: dict
        """
        kwargs = {}
        for k, v in annotations.items():
            try:
                _, class_name, primary_key, model_kwarg = k.split('-', 3)
                model_kwarg = model_kwarg.replace('-', '_')

                # Make sure we the data is for this instance
                if (model_instance.__class__.__name__.lower() != class_name and
                        not listing):
                    continue
                elif not listing:
                    if model_instance.primary_key != primary_key:
                        continue

                # Deserialize any json structs
                if v.startswith('json:'):
                    v = json.loads(v[5:])

                if model_kwarg in model_instance._attribute_map.keys():
                    kwargs[model_kwarg] = v
            except ValueError:
                # This means it is not a commissaire model annotaiton.
                pass
        return kwargs

    def _format_model(self, resp_data, model_instance, listing=False):
        """
        Takes a model instance and figures out the proper request.

        :param resp_data: Response data from the requests call.
        :type resp_data: dict
        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :param listing: Notes if this is an attempt to get a list of items.
        :type listing: bool
        :returns: The model instance
        :rtype: commissaire.model.Model
        """
        annotations = resp_data.get('metadata', {}).get('annotations', {})
        if not annotations:
            raise KeyError('No annotations for {0}'.format(
                model_instance.primary_key))

        kwargs = self._format_kwargs(
            model_instance,
            annotations, listing)
        # Host is special in that it has sensitive data stored in secrets
        if model_instance.__class__.__name__ == 'Host':
            secrets = self._get_secret(model_instance.primary_key)
            kwargs.update(secrets)

        if not kwargs:
            raise KeyError('No data for model.')

        try:
            model = model_instance.__class__.new(**kwargs)
            # We must coerce types since annotations are
            # flaky with non strings
            model._coerce()
            return model
        except TypeError as te:
            raise KeyError(
                'Caught {0}: {1}'.format(
                    te.__class__.__name__, te.args[0]), te)

    def _store_secret(self, name, data):
        """
        Stores data in base64 encoded format inside a Kubernetes secret.

        :param name: The name of the secret.
        :type name: str
        :param data: Data to be stored in the secret.
        :type data: dict
        """
        encoded_data = {}
        for k, v in data.items():
            # We must replace underscores as Kubernetes does not allow for
            # in secrets names
            encoded_data[k.replace('_', '-')] = base64.encodebytes(v)

        return self._store.post(
            self._secrets_endpoint,
            json={
                'apiVersion': _API_VERSION,
                'kind': 'Secret',
                'metadata': {
                    'name': name,
                    'type': 'Opaque',
                },
                'data': encoded_data,
            })

    def _get_secret(self, name):
        """
        Gets a Kubernetes secret.

        :param name: The name of the secret.
        :type name: str
        """
        response = self._store.get(self._secrets_endpoint + '/' + name)

        if response.status_code != requests.codes.OK:
            raise KeyError('No secrets for {0}'.format(name))

        secrets = {}
        rj = response.json()

        # The we have a data key use it directly
        if 'data' in rj.keys():
            rj = rj['data']
        # If we have an items key pull the data from the first item
        # FIXME: Verify it's the right data :-)
        elif 'items' in rj.keys():
            rj = rj['items'][0]['data']

        for k, v in rj.items():
            secrets[k.replace('-', '_')] = base64.decodebytes(v)

        return secrets

    def _delete_secret(self, name):
        """
        Deletes a Kubernetes secret.

        :param name: The name of the secret.
        :type name: str
        """
        return self._store.delete(self._secrets_endpoint + '/' + name)

    def _dispatch(self, op, model_instance):
        """
        Dispatches to the correct operation method.

        :param op: The operation to handle. save, list, delete, get.
        :type op: str
        :param model_instance: Instance of the model to operate on.
        :type model_instance: commissaire.model.Model
        """
        class_name = model_instance.__class__.__name__
        func = getattr(self, '_{0}_on_namespace'.format(op))
        if class_name in ('Host', 'Hosts'):
            func = getattr(self, '_{0}_host'.format(op))
        return func(model_instance)

    def _save(self, model_instance):  # pragma: no cover
        """
        Saves data to kubernetes and returns back a saved model.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        return self._dispatch('save', model_instance)

    def _save_host(self, model_instance):  # pragma: no cover
        """
        Saves a host to kubernetes and returns back a saved model.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        full_patch = []
        data = {}
        patch_path = '/metadata/annotations'
        secrets = {}
        class_name = model_instance.__class__.__name__.lower()
        for x in model_instance._attribute_map.keys():
            annotation_key = 'commissaire-{0}-{1}-{2}'.format(
                class_name, model_instance.primary_key, x)
            annotation_value = getattr(model_instance, x)

            # XXX Skip sensitive information for general annotation storage
            #     and store them in secrets later
            if x in model_instance._hidden_attributes:
                secrets[x] = annotation_value
                continue
            # Skip any empty values
            elif annotation_value:
                data[annotation_key] = str(annotation_value)

        if secrets:
            response = self._store_secret(model_instance.primary_key, secrets)
            if response.status_code == requests.codes.CONFLICT:
                # It already exists.
                # TODO: log
                pass
            elif response.status_code != requests.codes.CREATED:
                raise KeyError('Unable to save secrets for {0}: {1}'.format(
                    model_instance.primary_key, response.status_code))

        full_patch.append({
            'op': 'add',
            'path': patch_path,
            'value': data})

        path = _model_mapper[model_instance.__class__.__name__]
        response = self._store.patch(
            self._endpoint + path + model_instance.primary_key,
            json=full_patch,
            headers={'Content-Type': 'application/json-patch+json'})
        return self._format_model(response.json(), model_instance)

    def _save_on_namespace(self, model_instance):
        """
        Saves data to a namespace and returns back a saved model.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """

        patch_path = "/metadata/annotations"
        path = _model_mapper[model_instance.__class__.__name__]
        class_name = model_instance.__class__.__name__.lower()

        r = self._store.get(self._endpoint + path)
        if not r.json().get('metadata', {}).get('annotations', {}):
            # Ensure we have an annotation container.
            if self._store.patch(
                self._endpoint + path,
                json=[{
                    'op': 'add',
                    'path': patch_path,
                    'value': {'commissaire-manager': 'yes'}
                }],
                headers={'Content-Type': 'application/json-patch+json'}
            ).status_code != 200:
                raise KeyError(
                    'Could creat annotation container for {0}={1}'.format(
                        class_name, model_instance.primary_key))

        response = None
        # NOTE: Kubernetes does not allow underscores in keys. To get past
        #       this we substitute _'s with -'s
        for x in model_instance._attribute_map.keys():
            annotation_key = 'commissaire-{0}-{1}-{2}'.format(
                class_name, model_instance.primary_key, x.replace('_', '-'))
            annotation_value = getattr(model_instance, x)

            # If the value is iterable (list, dict) turn it into a json string
            if hasattr(annotation_value, '__iter__'):
                annotation_value = 'json:' + json.dumps(annotation_value)

            # Skip any empty values
            if annotation_value:
                full_patch = [{
                    'op': 'add',
                    'path': patch_path + '/' + annotation_key,
                    'value': str(annotation_value)}]

                response = self._store.patch(
                    self._endpoint + path,
                    json=full_patch,
                    headers={'Content-Type': 'application/json-patch+json'})
                if response.status_code != requests.codes.OK:
                    # TODO log
                    print('Could not save annotation {0}: {1}'.format(
                        annotation_key, response.status_code))
        if response:
            return self._format_model(response.json(), model_instance)
        raise KeyError('Could not save annotations!')

    def _get(self, model_instance):  # pragma: no cover
        """
        Returns data from a store and returns back a model.

        :param model_instance: Model instance to search and return
        :type model_instance: commissaire.model.Model
        :returns: The model instance
        :rtype: commissaire.model.Model
        """
        return self._dispatch('get', model_instance)

    def _get_host(self, model_instance):  # pragma: no cover
        """
        Returns a host from a store and returns back a model.

        :param model_instance: Model instance to search and return
        :type model_instance: commissaire.model.Model
        :returns: The model instance
        :rtype: commissaire.model.Model
        """
        path = _model_mapper[model_instance.__class__.__name__]
        response = self._store.get(
            self._endpoint + path + model_instance.primary_key)
        return self._format_model(response.json(), model_instance)

    def _get_on_namespace(self, model_instance):
        """
        Returns data within a namespace from a store and returns back a model.

        :param model_instance: Model instance to search and return
        :type model_instance: commissaire.model.Model
        :returns: The model instance
        :rtype: commissaire.model.Model
        """
        path = _model_mapper[model_instance.__class__.__name__]
        response = self._store.get(
            self._endpoint + path)
        return self._format_model(response.json(), model_instance)

    def _delete(self, model_instance):  # pragma: no cover
        """
        Deletes data from a store.

        :param model_instance: Model instance to delete
        :type model_instance: commissaire.model.Model
        """
        model_instance = self._get(model_instance)
        return self._dispatch('delete', model_instance)

    def _delete_host(self, model_instance):  # pragma: no cover
        """
        Deletes a host from a store.

        :param model_instance: Model instance to delete
        :type model_instance: commissaire.model.Model
        """
        full_patch = []
        secrets = {}
        for x in model_instance._attribute_map.keys():
            patch_path = (
                '/metadata/annotations/commissaire-host-{0}-{1}'.format(
                    model_instance.primary_key, x))
            patch_value = getattr(model_instance, x)

            # XXX Skip sensitive information for general annotation storage
            #     and store them in secrets later
            if x in model_instance._hidden_attributes:
                secrets[x] = patch_value
                continue

            # Skip any empty values
            if not patch_value:
                continue

            full_patch.append({'op': 'remove', 'path': patch_path})

        if secrets:
            response = self._delete_secret(model_instance.primary_key)

            if response.status_code == requests.codes.NOT_FOUND:
                # This means it already is gone.
                # TODO: log
                pass
            elif response.status_code != requests.codes.OK:
                raise KeyError('Unable to delete secrets for {0}: {1}'.format(
                    model_instance.primary_key, response.status_code))

        response = self._store.patch(
            (self._endpoint + _model_mapper['Host'] +
                model_instance.primary_key),
            json=full_patch,
            headers={'Content-Type': 'application/json-patch+json'})
        if response.status_code != requests.codes.OK:
            raise KeyError(response.text)

    def _delete_on_namespace(self, model_instance):
        """
        Deletes data within a namespace from a store.

        :param model_instance: Model instance to delete
        :type model_instance: commissaire.model.Model
        """
        full_patch = []
        class_name = model_instance.__class__.__name__.lower()
        for x in model_instance._attribute_map.keys():
            patch_path = (
                '/metadata/annotations/commissaire-{0}-{1}-{2}'.format(
                    class_name, model_instance.primary_key, x))
            patch_value = str(getattr(model_instance, x))

            # Skip any empty values
            if not patch_value:
                continue

            full_patch.append({'op': 'remove', 'path': patch_path})

        path = _model_mapper[model_instance.__class__.__name__]
        response = self._store.patch(
            self._endpoint + path,
            json=full_patch,
            headers={'Content-Type': 'application/json-patch+json'})
        if response.status_code != requests.codes.OK:
            raise KeyError(response.text)

    def _list(self, model_instance):  # pragma: no cover
        """
        Lists data at a location in a store and returns back model instances.

        :param model_instance: Model instance to search for and list
        :type model_instance: commissaire.model.Model
        :returns: A list of models
        :rtype: list
        """
        return self._dispatch('list', model_instance)

    def _list_on_namespace(self, model_instance):
        results = []
        path = _model_mapper[model_instance.__class__.__name__]
        data = self._store.get(self._endpoint + path).json()
        items = {}
        # FIXME: This works but it's a hack
        for k, v in data.get('metadata', {}).get('annotations', {}).items():
            parts = k.split('-')
            if parts[1] == model_instance._list_class.__name__.lower():
                if not items.get(parts[2]):
                    items[parts[2]] = {}
                items[parts[2]][k] = v

        for item in items.values():
            try:
                results.append(self._format_model({
                    'metadata': {'annotations': item}},
                    model_instance._list_class.new(), True))
            except (TypeError, KeyError):
                # TODO: Add logging
                pass

        return model_instance.new(**{model_instance._list_attr: results})

    def _list_host(self, model_instance):
        """
        Lists data at a location in a store and returns back model instances.

        :param model_instance: Model instance to search for and list
        :type model_instance: commissaire.model.Model
        :returns: A list of models
        :rtype: list
        """
        hosts = []
        path = _model_mapper[model_instance.__class__.__name__]
        items = self._store.get(self._endpoint + path).json()
        for item in items.get('items'):
            try:
                hosts.append(self._format_model(item, Host.new(), True))
            except (TypeError, KeyError):
                # TODO: Add logging
                pass

        return Hosts.new(hosts=hosts)


StoreHandler = KubernetesStoreHandler
