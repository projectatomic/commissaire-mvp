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
Constants for test cases.
"""

import copy
import json

from commissaire.handlers.models import (
    Hosts, Host, Cluster, ClusterRestart, ClusterUpgrade, ClusterDeploy)


def make_new(instance):
    """
    Returns a new deepcopy of an instance.
    """
    return copy.deepcopy(instance)


#: Response JSON for a single host
HOST_JSON = (
    '{"address": "10.2.0.2",'
    ' "status": "available", "os": "atomic",'
    ' "cpus": 2, "memory": 11989228, "space": 487652,'
    ' "last_check": "2015-12-17T15:48:18.710454"}')
#: Credential JSON for tests
HOST_CREDS_JSON = '{"remote_user": "root", "ssh_priv_key": "dGVzdAo="}'
#: Host model for most tests
HOST = Host(
    ssh_priv_key='dGVzdAo=',
    remote_user='root',
    **json.loads(HOST_JSON))
#: Hosts model for most tests
HOSTS = Hosts(
    hosts=[HOST]
)
#: Cluster model for most tests
CLUSTER = Cluster(
    name='cluster',
    status='ok',
    hostset=[],
)
#: Cluster model with HOST for most tests
CLUSTER_WITH_HOST = Cluster(
    name='cluster',
    status='ok',
    hostset=[HOST],
)
#: Cluster model with flattened HOST for tests
CLUSTER_WITH_FLAT_HOST = Cluster(
    name='cluster',
    status='ok',
    hostset=[HOST.address],
)
#: ClusterRestart model for most tests
CLUSTER_RESTART = ClusterRestart(
    name='cluster',
    status='ok',
    restarted=[],
    in_process=[],
    started_at='',
    finished_at= ''
)
#: ClusterUpgrade model for most tests
CLUSTER_UPGRADE = ClusterUpgrade(
    name='cluster',
    status='ok',
    upgraded=[],
    in_process=[],
    started_at='',
    finished_at= ''
)
#: ClusterDeploy model for most tests
CLUSTER_DEPLOY = ClusterDeploy(
    name='cluster',
    status='ok',
    version='1.0',
    deployed=[],
    in_process=[],
    started_at='',
    finished_at= ''
)
