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
The investigator job.
"""
import json
import datetime
import logging
import sys

from time import sleep

from commissaire import constants as C
from commissaire.handlers import util
from commissaire.handlers.models import Host
from commissaire.oscmd import get_oscmd
from commissaire.queues import WATCHER_QUEUE
from commissaire.transport import ansibleapi
from commissaire.util.ssh import TemporarySSHKey


def investigator(queue, run_once=False):
    """
    Investigates new hosts to retrieve and store facts.

    :param queue: Queue to pull work from.
    :type queue: Queue.Queue
    """
    logger = logging.getLogger('investigator')
    logger.info('Investigator started')

    while True:
        # Statuses follow:
        # http://commissaire.readthedocs.org/en/latest/enums.html#host-statuses
        store_manager, to_investigate, ssh_priv_key, remote_user = queue.get()
        address = to_investigate['address']
        logger.info('{0} is now in investigating.'.format(address))
        logger.debug(
            'Investigation details: key={0}, data={1}, remote_user={2}'.format(
                to_investigate, ssh_priv_key, remote_user))

        transport = ansibleapi.Transport(remote_user)

        try:
            host = store_manager.get(
                Host(
                    address=address,
                    status='',
                    os='',
                    cpus=0,
                    memory=0,
                    space=0,
                    last_check='',
                    ssh_priv_key='',
                    remote_user=''))
            key = TemporarySSHKey(host, logger)
            key.create()
        except Exception as error:
            logger.warn(
                'Unable to continue for {0} due to '
                '{1}: {2}. Returning...'.format(address, type(error), error))
            key.remove()
            continue

        try:
            result, facts = transport.get_info(address, key.path)
            # recreate the host instance with new data
            data = json.loads(host.to_json(secure=True))
            data.update(facts)
            host = Host(**data)
            host.last_check = datetime.datetime.utcnow().isoformat()
            host.status = 'bootstrapping'
            logger.info('Facts for {0} retrieved'.format(address))
            logger.debug('Data: {0}'.format(host.to_json()))
        except:
            exc_type, exc_msg, tb = sys.exc_info()
            logger.warn('Getting info failed for {0}: {1}'.format(
                address, exc_msg))
            host.status = 'failed'
            store_manager.save(host)
            key.remove()
            if run_once:
                break
            continue

        store_manager.save(host)
        logger.info(
            'Finished and stored investigation data for {0}'.format(address))
        logger.debug('Finished investigation update for {0}: {1}'.format(
            address, host.to_json()))

        logger.info('{0} is now in bootstrapping'.format(address))
        oscmd = get_oscmd(host.os)
        try:
            result, facts = transport.bootstrap(
                address, key.path, store_manager, oscmd)
            host.status = 'inactive'
            store_manager.save(host)
        except:
            exc_type, exc_msg, tb = sys.exc_info()
            logger.warn('Unable to start bootstraping for {0}: {1}'.format(
                address, exc_msg))
            host.status = 'disassociated'
            store_manager.save(host)
            key.remove()
            if run_once:
                break
            continue

        try:
            cluster = util.cluster_for_host(address, store_manager)
            cluster_type = cluster.type
        except KeyError as ke:
            logger.debug(
                '{0} not part of a cluster. Assuming {1}. "{2}"'.format(
                    host.address, C.CLUSTER_TYPE_HOST, ke))
            # Not part of a cluster. Assume host_only
            cluster_type = C.CLUSTER_TYPE_HOST

        # Verify association with relevant container managers
        for con_mgr in store_manager.list_container_managers(cluster_type):
            try:
                # Try 3 times waiting 5 seconds each time before giving up
                for cnt in range(0, 3):
                    if con_mgr.node_registered(address):
                        logger.info(
                            '{0} has been registered with the '
                            'container manager.'.format(address))
                        host.status = 'active'
                        break
                    if cnt == 3:
                        msg = 'Could not register with the container manager'
                        logger.warn(msg)
                        raise Exception(msg)
                    logger.debug(
                        '{0} has not been registered with the container '
                        ' manager. Checking again in 5 seconds...'.format(
                            address))
                    sleep(5)
            except:
                _, exc_msg, _ = sys.exc_info()
                logger.warn(
                    'Unable to finish bootstrap for {0} while associating '
                    'with the {1}: {2}'.format(
                        address, con_mgr.__class__.__name__, exc_msg))
                host.status = 'inactive'

        store_manager.save(host)
        logger.info(
            'Finished bootstrapping for {0}'.format(address))
        logging.debug('Finished bootstrapping for {0}: {1}'.format(
            address, host.to_json()))

        WATCHER_QUEUE.put_nowait((host, datetime.datetime.utcnow()))

        key.remove()
        if run_once:
            logger.info('Exiting due to run_once request.')
            break

    logger.info('Investigator stopping')
