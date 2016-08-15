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
Resource utilities.
"""
import cherrypy
import falcon

from commissaire.handlers.models import Cluster, Clusters, Host


def etcd_host_key(address):
    """
    Returns the etcd key for the given host address.

    :param address: Address of a host
    :type address: str
    """
    return '/commissaire/hosts/{0}'.format(address)


def etcd_cluster_key(name):
    """
    Returns the etcd key for the given cluster name.

    :param name: Name of a cluster
    :type name: str
    """
    return '/commissaire/clusters/{0}'.format(name)


def etcd_cluster_exists(name):
    """
    Returns whether a cluster with the given name exists.

    :param name: Name of a cluster
    :type name: str
    """
    store_manager = cherrypy.engine.publish('get-store-manager')[0]
    try:
        store_manager.get(Cluster.new(name=name))
    except:
        return False
    return True


def cluster_for_host(address, store_manager):
    """
    Checks to see if the the host is part of a cluster. KeyError is raised
    if the host is not part of a cluster.

    :param name: Name of a cluster
    :type name: str
    :param store_manager: Remote object for remote stores
    :type store_manager: commissaire.store.StoreHandlerManager
    :returns: A cluster instance that has the host
    :rtype: commissaire.model.Model
    :rasies: KeyError
    """
    for cluster in store_manager.list(Clusters.new()).clusters:
        if address in cluster.hostset:
            return cluster

    raise KeyError


def etcd_cluster_has_host(name, address):
    """
    Checks if a host address belongs to a cluster with the given name.
    If no such cluster exists, the function raises KeyError.

    :param name: Name of a cluster
    :type name: str
    :param address: Host address
    :type address: str
    """
    try:
        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        cluster = store_manager.get(Cluster.new(name=name))
    except:
        raise KeyError

    return address in cluster.hostset


def etcd_cluster_add_host(name, address):
    """
    Adds a host address to a cluster with the given name.
    If no such cluster exists, the function raises KeyError.

    Note the function is idempotent: if the host address is
    already in the cluster, no change occurs.

    :param name: Name of a cluster
    :type name: str
    :param address: Host address to add
    :type address: str
    """
    try:
        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        cluster = store_manager.get(Cluster.new(name=name))
    except:
        raise KeyError

    # FIXME: Need input validation.
    #        - Does the host exist at /commissaire/hosts/{IP}?
    #        - Does the host already belong to another cluster?

    # FIXME: Should guard against races here, since we're fetching
    #        the cluster record and writing it back with some parts
    #        unmodified.  Use either locking or a conditional write
    #        with the etcd 'modifiedIndex'.  Deferring for now.

    if address not in cluster.hostset:
        cluster.hostset.append(address)
        cluster = store_manager.save(cluster)


def etcd_cluster_remove_host(name, address):
    """
    Removes a host address from a cluster with the given name.
    If no such cluster exists, the function raises KeyError.

    Note the function is idempotent: if the host address is
    not in the cluster, no change occurs.


    :param name: Name of a cluster
    :type name: str
    :param address: Host address to remove
    :type address: str
    """
    cluster = get_cluster_model(name)
    if not cluster:
        raise KeyError

    # FIXME: Should guard against races here, since we're fetching
    #        the cluster record and writing it back with some parts
    #        unmodified.  Use either locking or a conditional write
    #        with the etcd 'modifiedIndex'.  Deferring for now.

    if address in cluster.hostset:
        cluster.hostset.remove(address)
        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        store_manager.save(cluster)


def get_cluster_model(name):
    """
    Returns a Cluster instance from the etcd record for the given
    cluster name, if it exists, or else None.

    For convenience, the EtcdResult is embedded in the Cluster instance
    as an 'etcd' property.

    :param name: Name of a cluster
    :type name: str
    """
    store_manager = cherrypy.engine.publish('get-store-manager')[0]
    try:
        cluster = store_manager.get(Cluster.new(name=name))
    except:
        cluster = None

    return cluster


def etcd_host_create(address, ssh_priv_key, remote_user, cluster_name=None):
    """
    Creates a new host record in etcd and optionally adds the host to
    the specified cluster.  Returns a (status, host) tuple where status
    is the Falcon HTTP status and host is a Host model instance, which
    may be None if an error occurred.

    This function is idempotent so long as the host parameters agree
    with an existing host record and cluster membership.

    :param address: Host address.
    :type address: str
    :param ssh_priv_key: Host's SSH key, base64-encoded.
    :type ssh_priv_key: str
    :param remote_user: The user to use with SSH.
    :type remote_user: str
    :param cluster_name: Name of the cluster to join, or None
    :type cluster_name: str or None
    :return: (status, host)
    :rtype: tuple
    """
    store_manager = cherrypy.engine.publish('get-store-manager')[0]

    try:
        # Check if the request conflicts with the existing host.
        existing_host = store_manager.get(Host.new(address=address))
        if existing_host.ssh_priv_key != ssh_priv_key:
            return (falcon.HTTP_409, None)
        if cluster_name:
            try:
                assert etcd_cluster_has_host(cluster_name, address)
            except (AssertionError, KeyError):
                return (falcon.HTTP_409, None)

        # Request is compatible with the existing host, so
        # we're done.  (Not using HTTP_201 since we didn't
        # actually create anything.)
        return (falcon.HTTP_200, existing_host)
    except:
        pass

    # Verify the cluster exists, if given.  Do it now
    # so we can fail before writing anything to etcd.
    if cluster_name:
        cluster = get_cluster_model(cluster_name)
        if cluster is None:
            return (falcon.HTTP_409, None)
    else:
        cluster = None

    host = Host.new(
        address=address,
        ssh_priv_key=ssh_priv_key,
        status='investigating',
        remote_user=remote_user)

    def callback(store_manager, host, exception):
        if exception is None:
            store_manager.save(host)

            # Add host to the requested cluster.
            if cluster_name:
                etcd_cluster_add_host(cluster_name, host.address)

    cherrypy.engine.publish(
        'investigator-submit', store_manager, host, cluster, callback)

    return (falcon.HTTP_201, host)
