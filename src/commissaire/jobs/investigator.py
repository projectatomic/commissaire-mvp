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
import os
import sys
import tempfile

from time import sleep

from commissaire import constants as C
from commissaire.compat.b64 import base64
from commissaire.containermgr.kubernetes import KubeContainerManager
from commissaire.handlers import util
from commissaire.handlers.models import Host
from commissaire.oscmd import get_oscmd
from commissaire.transport import ansibleapi


def clean_up_key(key_file):
    """
    Remove the key file.

    :param key_file: Full path to the key_file
    :type key_file: str
    """
    logger = logging.getLogger('investigator')
    try:
        os.unlink(key_file)
        logger.debug('Removed temporary key file {0}'.format(key_file))
    except:
        exc_type, exc_msg, tb = sys.exc_info()
        logger.warn(
            'Unable to remove the temporary key file: '
            '{0}. Exception:{1}'.format(key_file, exc_msg))


def investigator(queue, config, run_once=False):
    """
    Investigates new hosts to retrieve and store facts.

    :param queue: Queue to pull work from.
    :type queue: Queue.Queue
    :param config: Configuration information.
    :type config: commissaire.config.Config
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

        f = tempfile.NamedTemporaryFile(prefix='key', delete=False)
        key_file = f.name
        logger.debug(
            'Using {0} as the temporary key location for {1}'.format(
                key_file, address))
        f.write(base64.decodestring(ssh_priv_key))
        logger.info('Wrote key for {0}'.format(address))
        f.close()

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
        except Exception as error:
            logger.warn(
                'Unable to continue for {0} due to '
                '{1}: {2}. Returning...'.format(address, type(error), error))
            clean_up_key(key_file)
            continue

        try:
            result, facts = transport.get_info(address, key_file)
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
            clean_up_key(key_file)
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
                address, key_file, config, oscmd, store_manager)
            host.status = 'inactive'
            store_manager.save(host)
        except:
            exc_type, exc_msg, tb = sys.exc_info()
            logger.warn('Unable to start bootstraping for {0}: {1}'.format(
                address, exc_msg))
            host.status = 'disassociated'
            store_manager.save(host)
            clean_up_key(key_file)
            if run_once:
                break
            continue

        host.status = cluster_type = C.CLUSTER_TYPE_HOST
        try:
            cluster = util.cluster_for_host(address, store_manager)
            cluster_type = cluster.type
        except KeyError:
            # Not part of a cluster
            pass

        # Verify association with the container manager
        if cluster_type == C.CLUSTER_TYPE_KUBERNETES:
            try:
                container_mgr = KubeContainerManager(config)
                # Try 3 times waiting 5 seconds each time before giving up
                for cnt in range(0, 3):
                    if container_mgr.node_registered(address):
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
                    'with the container manager: {1}'.format(
                        address, exc_msg))
                host.status = 'inactive'

        store_manager.save(host)
        logger.info(
            'Finished bootstrapping for {0}'.format(address))
        logging.debug('Finished bootstrapping for {0}: {1}'.format(
            address, host.to_json()))

        clean_up_key(key_file)
        if run_once:
            logger.info('Exiting due to run_once request.')
            break

    logger.info('Investigator stopping')
