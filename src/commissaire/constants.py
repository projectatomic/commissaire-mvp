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
Constants for Commissaire.
"""

#: Cluster type for host nodes only
CLUSTER_TYPE_HOST = 'host_only'
#: Cluster type for host nodes with kubernetes as the container manager
CLUSTER_TYPE_KUBERNETES = 'kubernetes'
#: Cluster type to use if none is specified
CLUSTER_TYPE_DEFAULT = CLUSTER_TYPE_KUBERNETES

# Default etcd configuration
DEFAULT_ETCD_STORE_HANDLER = {
    'name': 'commissaire.store.etcdstorehandler',
    'protocol': 'http',
    'host': '127.0.0.1',
    'port': 2379,
    'models': []
}

# Default Kubernetes configuration
DEFAULT_KUBERNETES_STORE_HANDLER = {
    'name': 'commissaire.store.kubestorehandler',
    'protocol': 'http',
    'host': '127.0.0.1',
    'port': 8080,
    'models': ['*']
}
