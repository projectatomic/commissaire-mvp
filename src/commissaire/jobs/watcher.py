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
The watcher job.
"""
import datetime
import logging
import time

from commissaire import constants as C
from commissaire.handlers.models import Hosts
from commissaire.handlers import util
from commissaire.transport import ansibleapi
from commissaire.util.ssh import TemporarySSHKey
from commissaire.queues import Empty


def watcher(queue, store_manager, run_once=False):
    """
    Attempts to connect and check hosts for status.

    :param queue: Queue to pull work from.
    :type queue: Queue.Queue
    :param store_manager: Proxy object for remtote stores
    :type store_manager: commissaire.store.StoreHandlerManager
    :param run_once: If only one run should occur.
    :type run_once: bool
    """
    logger = logging.getLogger('watcher')
    logger.info('Watcher started')
    # TODO: should be configurable
    delta = datetime.timedelta(seconds=20)
    # TODO: should be configurable
    throttle = 60  # 1 minute

    # If the queue is empty attempt to populated it with known hosts
    if queue.qsize() == 0:
        logger.info('The WATCHER_QUEUE is empty. '
                    'Attempting to populate it from the store.')
        try:
            hosts = store_manager.list(Hosts(hosts=[]))
            for host in hosts.hosts:
                last_check = datetime.datetime.strptime(
                    host.last_check, "%Y-%m-%dT%H:%M:%S.%f")
                queue.put_nowait((host, last_check))
                logger.debug('Inserted {0} into WATCHER_QUEUE'.format(
                    host.address))
        except:
            logger.info('No hosts found in the store.')

    while True:
        try:
            host, last_run = queue.get_nowait()
        except Empty:
            time.sleep(throttle)
            continue

        logger.debug('Retrieved {0} from queue. Last check was {1}'.format(
            host.address, last_run))
        now = datetime.datetime.utcnow()
        if last_run > now - delta:
            logger.debug('{0} not ready to check. {1}'.format(
                host.address, last_run))
            # Requeue the host with the same last_run
            queue.put_nowait((host, last_run))
        else:
            logger.info('Checking {0} for availability'.format(
                host.address))
            transport = ansibleapi.Transport(host.remote_user)
            with TemporarySSHKey(host, logger) as key:
                results = transport.check_host_availability(host, key.path)
                host.last_check = now.isoformat()
                if results[0] == 0:  # This means the host is available
                    # Only flip the bit on failed only
                    if host.status == 'failed':
                        try:
                            cluster_type = util.cluster_for_host(
                                host.address, store_manager).type
                        except Exception:
                            logger.debug(
                                '{0} has no cluster type. Assuming {1}'.format(
                                    host.address, C.CLUSTER_TYPE_HOST))
                            cluster_type = C.CLUSTER_TYPE_HOST
                        # If the type is CLUSTER_TYPE_HOST then it should be
                        if cluster_type == C.CLUSTER_TYPE_HOST:
                            host.status = 'disassociated'
                        else:
                            host.status = 'active'
                else:
                    # If we can not access the host at all throw it to failed
                    host.status = 'failed'
                host.last_check = now.isoformat()
                host = store_manager.save(host)
                # Requeue the host
                queue.put_nowait((host, now))
                logger.debug('{0} has been requeued for next check run'.format(
                    host.address))

        if run_once:
            logger.info('Exiting watcher due to run_once request.')
            break

        logger.debug('Sleeping for {0} seconds.'.format(throttle))
        time.sleep(throttle)

    logger.info('Watcher stopping')
