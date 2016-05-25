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
Models for handlers.
"""

import json

import cherrypy

from commissaire.model import Model


class Cluster(Model):
    """
    Representation of a Cluster.
    """
    _json_type = dict
    _attributes = ('status', 'hostset')
    _hidden_attributes = ('hostset',)
    _key = '/commissaire/clusters/{0}'

    def __init__(self, **kwargs):
        Model.__init__(self, **kwargs)
        # Hosts is always calculated, not stored in etcd.
        self.hosts = {'total': 0,
                      'available': 0,
                      'unavailable': 0}

    # FIXME Generalize and move to Model?
    def to_json_with_hosts(self, secure=False):
        data = {}
        for key in self._attributes:
            if secure:
                data[key] = getattr(self, key)
            elif key not in self._hidden_attributes:
                data[key] = getattr(self, key)
        data['hosts'] = self.hosts
        return json.dumps(data)

    def save(self, *parts):
        """
        Saves the model to the object store.

        :raises: Exception if unable to save
        :returns: Itself
        :rtype: model
        """
        key = self._key.format(*parts)
        etcd_resp, error = cherrypy.engine.publish(
            'store-save', key, self.to_json(secure=True))[0]
        if error:
            raise Exception(error)
        return self


class ClusterDeploy(Model):
    """
    Representation of a Cluster deploy operation.
    """
    _json_type = dict
    _attributes = (
        'status', 'version', 'deployed', 'in_process',
        'started_at', 'finished_at')
    _key = '/commissaire/cluster/{0}/deploy'


class ClusterRestart(Model):
    """
    Representation of a Cluster restart operation.
    """
    _json_type = dict
    _attributes = (
        'status', 'restarted', 'in_process',
        'started_at', 'finished_at')
    _key = '/commissaire/cluster/{0}/restart'


class ClusterUpgrade(Model):
    """
    Representation of a Cluster upgrade operation.
    """
    _json_type = dict
    _attributes = (
        'status', 'upgraded', 'in_process', 'started_at', 'finished_at')
    _key = '/commissaire/cluster/{0}/upgrade'


class Clusters(Model):
    """
    Representation of a group of one or more Clusters.
    """
    _json_type = list
    _attributes = ('clusters',)
    _key = '/commissaire/clusters/'

    @classmethod
    def retrieve(klass, *parts):
        """
        Gets a list of hosts from the store.

        :raises: Exception if unable to save
        :returns: Itself
        :rtype: model
        """
        key = klass._key.format(*parts)
        etcd_resp, error = cherrypy.engine.publish('store-list', key)[0]
        if error:
            raise Exception(error)
        clusters = []
        for x in etcd_resp.children:
            if etcd_resp.key != x.key:
                name = x.key.split('/')[-1]
                if name:
                    clusters.append(name)
        return klass(clusters=clusters)


class Host(Model):
    """
    Representation of a Host.
    """
    _json_type = dict
    _attributes = (
        'address', 'status', 'os', 'cpus', 'memory',
        'space', 'last_check', 'ssh_priv_key', 'remote_user')
    _hidden_attributes = ('ssh_priv_key', 'remote_user')
    _key = '/commissaire/hosts/{0}'


class Hosts(Model):
    """
    Representation of a group of one or more Hosts.
    """
    _json_type = list
    _attributes = ('hosts', )
    _key = '/commissaire/hosts/'

    @classmethod
    def retrieve(klass, *parts):
        """
        Gets the model from the object store.

        :raises: Exception if unable to save
        :returns: Itself
        :rtype: model
        """
        key = klass._key.format(*parts)
        hosts = []
        etcd_resp, error = cherrypy.engine.publish('store-get', key)[0]

        for host in etcd_resp.children:
            hosts.append(Host(**json.loads(host.value)))

        return klass(hosts=hosts)


class Status(Model):
    """
    Representation of a Host.
    """
    _json_type = dict
    _attributes = (
        'etcd', 'investigator')
