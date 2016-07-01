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
The clusterexec job.
"""

import datetime
import logging
import tempfile

from commissaire.handlers.models import (
    ClusterDeploy, ClusterUpgrade, ClusterRestart, Cluster, Hosts)
from commissaire.transport import ansibleapi
from commissaire.compat.b64 import base64
from commissaire.oscmd import get_oscmd


def clusterexec(store_manager, cluster_name, command, kwargs={}):
    """
    Remote executes a shell commands across a cluster.

    :param store_manager: Proxy object for remtote stores
    :type store_manager: commissaire.store.StoreHandlerManager
    :param cluster_name: Name of the cluster to act on
    :type cluster_name: str
    :param command: Top-level command to execute
    :type command: str
    :param kwargs: Keyword arguments for the command
    :type kwargs: dict
    """
    logger = logging.getLogger('clusterexec')

    # TODO: This is a hack and should really be done elsewhere
    command_args = ()
    if command == 'upgrade':
        finished_hosts_key = 'upgraded'
        model_instance = ClusterUpgrade(
            name=cluster_name,
            status='in_process',
            upgraded=[],
            in_process=[],
            started_at=datetime.datetime.utcnow().isoformat(),
            finished_at=None
        )
    elif command == 'restart':
        finished_hosts_key = 'restarted'
        model_instance = ClusterRestart(
            name=cluster_name,
            status='in_process',
            restarted=[],
            in_process=[],
            started_at=datetime.datetime.utcnow().isoformat(),
            finished_at=None
        )
    elif command == 'deploy':
        finished_hosts_key = 'deployed'
        version = kwargs.get('version')
        command_args = (version,)
        model_instance = ClusterDeploy(
            name=cluster_name,
            status='in_process',
            version=version,
            deployed=[],
            in_process=[],
            started_at=datetime.datetime.utcnow().isoformat(),
            finished_at=None
        )

    end_status = 'finished'

    try:
        # Set the initial status in the store
        logger.info('Setting initial status.')
        logger.debug('Status={0}'.format(model_instance.to_json()))
        store_manager.save(model_instance)
    except Exception as error:
        logger.error(
            'Unable to save initial state for "{0}" clusterexec due to '
            '{1}: {2}'.format(cluster_name, type(error), error))
        return

    # Collect all host addresses in the cluster
    try:
        cluster = store_manager.get(Cluster(
            name=cluster_name, status='', hostset=[]))
    except Exception as error:
        logger.warn(
            'Unable to continue for cluster "{0}" due to '
            '{1}: {2}. Returning...'.format(cluster_name, type(error), error))
        return

    if cluster.hostset:
        logger.debug(
            '{0} hosts in cluster "{1}"'.format(
                len(cluster.hostset), cluster_name))
    else:
        logger.warn('No hosts in cluster "{0}"'.format(cluster_name))

    # TODO: Find better way to do this
    try:
        hosts = store_manager.list(Hosts(hosts=[]))
    except Exception as error:
        logger.warn(
            'No hosts in the cluster. Error: {0}. Exiting clusterexec'.format(
                error))
        return

    for host in hosts.hosts:
        if host.address not in cluster.hostset:
            logger.debug(
                'Skipping {0} as it is not in this cluster.'.format(
                    host.address))
            continue  # Move on to the next one
        oscmd = get_oscmd(host.os)

        # command_list is only used for logging
        command_list = getattr(oscmd, command)(*command_args)
        logger.info('Executing {0} on {1}...'.format(
            command_list, host.address))

        model_instance.in_process.append(host.address)
        try:
            store_manager.save(model_instance)
        except Exception as error:
            logger.error(
                'Unable to save in_process state for "{0}" clusterexec due to '
                '{1}: {2}'.format(cluster_name, type(error), error))
            return

        # TODO: This is reused, make it reusable
        f = tempfile.NamedTemporaryFile(prefix='key', delete=False)
        key_file = f.name
        logger.debug(
            'Using {0} as the temporary key location for {1}'.format(
                key_file, host.address))
        f.write(base64.decodestring(host.ssh_priv_key))
        logger.debug('Wrote key for {0}'.format(host.address))
        f.close()

        try:
            transport = ansibleapi.Transport(host.remote_user)
            exe = getattr(transport, command)
            result, facts = exe(
                host.address, key_file, oscmd, kwargs)
        # XXX: ansibleapi explicitly raises Exception()
        except Exception as ex:
            # If there was a failure set the end_status and break out
            end_status = 'failed'
            logger.error('Clusterexec {0} for {1} failed: {2}: {3}'.format(
                command, host.address, type(ex), ex))
            break
        finally:
            try:
                f.unlink(key_file)
                logger.debug('Removed temporary key file {0}'.format(key_file))
            except:
                logger.warn(
                    'Unable to remove the temporary key file: {0}'.format(
                        key_file))

        # Set the finished hosts
        new_finished_hosts = getattr(
            model_instance, finished_hosts_key) + [host.address]
        setattr(
            model_instance,
            finished_hosts_key,
            new_finished_hosts)
        try:
            idx = model_instance.in_process.index(host.address)
            model_instance.in_process.pop(idx)
        except ValueError:
            logger.warn('Host {0} was not in_process for {1} {2}'.format(
                host['address'], command, cluster_name))
        try:
            store_manager.save(model_instance)
            logger.info('Finished executing {0} for {1} in {2}'.format(
                command, host.address, cluster_name))
        except Exception as error:
            logger.error(
                'Unable to save cluster state for "{0}" clusterexec due to '
                '{1}: {2}'.format(cluster_name, type(error), error))
            return

    # Final set of command result
    model_instance.finished_at = datetime.datetime.utcnow().isoformat()
    model_instance.status = end_status

    logger.info('Cluster {0} final {1} status: {2}'.format(
        cluster_name, command, model_instance.to_json()))

    try:
        store_manager.save(model_instance)
    except Exception as error:
        logger.error(
            'Unable to save final state for "{0}" clusterexec due to '
            '{1}: {2}'.format(cluster_name, type(error), error))

    logger.info('Clusterexec stopping')
