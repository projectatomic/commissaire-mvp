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

from commissaire import constants as C
from commissaire.model import Model


class Cluster(Model):
    """
    Representation of a Cluster.
    """
    _json_type = dict
    _attribute_map = {
        'name': {'type': basestring},
        'status': {'type': basestring},
        'type': {'type': basestring},
        'hostset': {'type': list},
    }
    _hidden_attributes = ('hostset',)
    _attribute_defaults = {
        'name': '', 'type': C.CLUSTER_TYPE_DEFAULT,
        'status': '', 'hostset': []}
    _primary_key = 'name'

    def __init__(self, **kwargs):
        Model.__init__(self, **kwargs)
        # Hosts is always calculated, not stored in etcd.
        self.hosts = {'total': 0,
                      'available': 0,
                      'unavailable': 0}

    # FIXME Generalize and move to Model?
    def to_json_with_hosts(self, secure=False):
        data = {}
        for key in self._attribute_map.keys():
            if secure:
                data[key] = getattr(self, key)
            elif key not in self._hidden_attributes:
                data[key] = getattr(self, key)
        data['hosts'] = self.hosts
        return json.dumps(data)


class ClusterDeploy(Model):
    """
    Representation of a Cluster deploy operation.
    """
    _json_type = dict
    _attribute_map = {
        'name': {'type': basestring},
        'status': {'type': basestring},
        'version': {'type': basestring},
        'deployed': {'type': list},
        'in_process': {'type': list},
        'started_at': {'type': basestring},
        'finished_at': {'type': basestring},
    }
    _attribute_defaults = {
        'name': '', 'status': '', 'version': '',
        'deployed': [], 'in_process': [], 'started_at': '', 'finished_at': ''}
    _primary_key = 'name'


class ClusterRestart(Model):
    """
    Representation of a Cluster restart operation.
    """
    _json_type = dict
    _attribute_map = {
        'name': {'type': basestring},
        'status': {'type': basestring},
        'restarted': {'type': list},
        'in_process': {'type': list},
        'started_at': {'type': basestring},
        'finished_at': {'type': basestring},
    }

    _attribute_defaults = {
        'name': '', 'status': '', 'restarted': [],
        'in_process': [], 'started_at': '', 'finished_at': ''}
    _primary_key = 'name'


class ClusterUpgrade(Model):
    """
    Representation of a Cluster upgrade operation.
    """
    _json_type = dict
    _attribute_map = {
        'name': {'type': basestring},
        'status': {'type': basestring},
        'upgraded': {'type': list},
        'in_process': {'type': list},
        'started_at': {'type': basestring},
        'finished_at': {'type': basestring},
    }

    _attribute_defaults = {
        'name': '', 'status': '', 'upgraded': [],
        'in_process': [], 'started_at': '', 'finished_at': ''}
    _primary_key = 'name'


class Clusters(Model):
    """
    Representation of a group of one or more Clusters.
    """
    _json_type = list
    _attribute_map = {
        'clusters': {'type': list},
    }
    _attribute_defaults = {'clusters': []}
    _list_attr = 'clusters'
    _list_class = Cluster


class Host(Model):
    """
    Representation of a Host.
    """
    _json_type = dict
    _attribute_map = {
        'address': {'type': basestring},
        'status': {'type': basestring},
        'os': {'type': basestring},
        'cpus': {'type': int},
        'memory': {'type': int},
        'space': {'type': int},
        'last_check': {'type': basestring},
        'ssh_priv_key': {'type': basestring},
        'remote_user': {'type': basestring},
    }
    _attribute_defaults = {
        'address': '', 'status': '', 'os': '', 'cpus': 0,
        'memory': 0, 'space': 0, 'last_check': '', 'ssh_priv_key': '',
        'remote_user': 'root'}
    _hidden_attributes = ('ssh_priv_key', 'remote_user')
    _primary_key = 'address'


class Hosts(Model):
    """
    Representation of a group of one or more Hosts.
    """
    _json_type = list
    _attribute_map = {
        'hosts': {'type': list},
    }
    _attribute_defaults = {'hosts': []}
    _list_attr = 'hosts'
    _list_class = Host


class Status(Model):
    """
    Representation of a Host.
    """
    _json_type = dict
    _attribute_map = {
        'etcd': {'type': dict},
        'investigator': {'type': dict},
        'watcher': {'type': dict},
    }
    _attribute_defaults = {'etcd': {}, 'investigator': {}, 'watcher': {}}
