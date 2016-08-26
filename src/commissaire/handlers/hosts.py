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
Host(s) handlers.
"""

import json

import cherrypy
import falcon

import commissaire.handlers.util as util

from commissaire import constants as C
from commissaire.resource import Resource
from commissaire.handlers.models import Host, HostStatus, Hosts, Clusters
from commissaire.queues import WATCHER_QUEUE


class HostsResource(Resource):
    """
    Resource for working with Hosts.
    """

    def on_get(self, req, resp):
        """
        Handles GET requests for Hosts.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        """

        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            hosts = store_manager.list(Hosts(hosts=[]))
            if len(hosts.hosts) == 0:
                raise Exception()
            resp.status = falcon.HTTP_200
            req.context['model'] = hosts
        except Exception:
            # This was originally a "no content" but I think a 404 makes
            # more sense if there are no hosts
            self.logger.warn(
                'Store does not have any hosts. Returning [] and 404.')
            resp.status = falcon.HTTP_404
            req.context['model'] = None
            return


class HostCredsResource(Resource):
    """
    Resource for getting credentials for a single host.
    """

    def on_get(self, req, resp, address):
        """
        Handles retrieval of existing Host credentials.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param address: The address of the Host being requested.
        :type address: str
        """
        # TODO: Verify input
        # TODO: Decide if this should be a model or if it makes sense to
        #       stay a subset off of Host and bypass the req.context
        #       middleware system.
        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            host = store_manager.get(Host.new(address=address))
            resp.status = falcon.HTTP_200
            body = {
                'ssh_priv_key': host.ssh_priv_key,
                'remote_user': host.remote_user or 'root',
            }
            resp.body = json.dumps(body)
        except:
            resp.status = falcon.HTTP_404
            return


class HostStatusResource(Resource):
    """
    Resource for getting status for a single host.
    """

    def on_get(self, req, resp, address):
        """
        Handles retrieval of existing Host status.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param address: The address of the Host being requested.
        :type address: str
        """
        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            host = store_manager.get(Host.new(address=address))
            self.logger.debug('StatusHost found host {0}'.format(host.address))
            status = HostStatus.new(
                host={
                    'last_check': host.last_check,
                    'status': host.status,
                })

            try:
                resp.status = falcon.HTTP_200
                cluster = util.cluster_for_host(host.address, store_manager)
                status.type = cluster.type
                self.logger.debug('Cluster type for {0} is {1}'.format(
                    host.address, status.type))

                if status.type != C.CLUSTER_TYPE_HOST:
                    try:
                        container_mgr = store_manager.list_container_managers(
                            cluster.type)[0]
                    except Exception as error:
                        self.logger.error(
                            'StatusHost for host {0} did not find a '
                            'container_mgr: {1}: {2}'.format(
                                host.address, type(error), error))
                        raise error
                    self.logger.debug(
                        'StatusHost for host {0} got container_mgr '
                        'instance {1}'.format(
                            host.address, type(container_mgr)))

                    is_raw = req.get_param_as_bool('raw') or False
                    self.logger.debug(
                        'StatusHost raw={0} found host {0} will'.format(
                            is_raw, host.address))

                    status_code, result = container_mgr.get_host_status(
                        host.address, is_raw)

                    # If we have a raw request ..
                    if is_raw:
                        # .. forward the http status as well or fall back to
                        # service unavailable
                        resp.status = getattr(
                            falcon.status_codes,
                            'HTTP_{0}'.format(status_code),
                            falcon.status_codes.HTTP_SERVICE_UNAVAILABLE)
                    status.container_manager = result
                else:
                    # Raise to be caught in host only type
                    raise KeyError
            except KeyError:
                # The host is not in a cluster.
                self.logger.info(
                    'Host {0} is not in a cluster. Defaulting to {1}'.format(
                        host.address, C.CLUSTER_TYPE_HOST))
                status.type = C.CLUSTER_TYPE_HOST

            self.logger.debug(
                'StatusHost end status code: {0} json={1}'.format(
                    resp.status, status.to_json()))

        except Exception as ex:
            self.logger.debug(
                'Host Status exception caught for {0}: {1}:{2}'.format(
                    host.address, type(ex), ex))
            resp.status = falcon.HTTP_404
            return

        self.logger.debug('Status for {0}: {1}'.format(
            host.address, status.to_json()))

        req.context['model'] = status


class HostResource(Resource):
    """
    Resource for working with a single Host.
    """

    def on_get(self, req, resp, address):
        """
        Handles retrieval of an existing Host.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param address: The address of the Host being requested.
        :type address: str
        """
        # If the host is still bootstrapping, the store handler
        # won't find it yet.  So respond with a fake host status.
        if cherrypy.engine.publish('investigator-is-pending', address)[0]:
            host = Host.new(address=address, status='investigating')
            resp.status = falcon.HTTP_200
            req.context['model'] = host
            return

        # TODO: Verify input
        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            # TODO: use some kind of global default for Hosts
            host = store_manager.get(Host.new(address=address))
            resp.status = falcon.HTTP_200
            req.context['model'] = host
        except:
            resp.status = falcon.HTTP_404
            return

    def on_put(self, req, resp, address):
        """
        Handles the creation of a new Host.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param address: The address of the Host being requested.
        :type address: str
        """
        try:
            # Extract what we need from the input data.
            # Don't treat it as a skeletal host record.
            req_data = req.stream.read()
            req_body = json.loads(req_data.decode())
            ssh_priv_key = req_body['ssh_priv_key']
            # Remote user is optional.
            remote_user = req_body.get('remote_user', 'root')
            # Cluster member is optional.
            cluster_name = req_body.get('cluster', None)
        except (KeyError, ValueError):
            self.logger.info(
                'Bad client PUT request for host {0}: {1}'.
                format(address, req_data))
            resp.status = falcon.HTTP_400
            return

        resp.status, host_model = util.etcd_host_create(
            address, ssh_priv_key, remote_user, cluster_name)

        req.context['model'] = host_model

    def on_delete(self, req, resp, address):
        """
        Handles the Deletion of a Host.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param address: The address of the Host being requested.
        :type address: str
        """
        resp.body = '{}'
        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        try:
            host = Host.new(address=address)
            WATCHER_QUEUE.dequeue(host)
            store_manager.delete(host)
            self.logger.debug(
                'Deleted host {0} and dequeued it from the watcher.'.format(
                    host.address))
            resp.status = falcon.HTTP_200
        except:
            resp.status = falcon.HTTP_404

        # Also remove the host from all clusters.
        # Note: We've done all we need to for the host deletion,
        #       so if an error occurs from here just log it and
        #       return.
        try:
            clusters = store_manager.list(Clusters(clusters=[]))
        except:
            self.logger.warn('Store does not have any clusters')
            return
        for cluster in clusters.clusters:
            try:
                self.logger.debug(
                    'Checking cluster {0}'.format(cluster.name))
                if address in cluster.hostset:
                    self.logger.info(
                        'Removing {0} from cluster {1}'.format(
                            address, cluster.name))
                    cluster.hostset.remove(address)
                    store_manager.save(cluster)
                    self.logger.info(
                        '{0} has been removed from cluster {1}'.format(
                            address, cluster.name))
            except:
                self.logger.warn(
                    'Failed to remove {0} from cluster {1}'.format(
                        address, cluster.name))


class ImplicitHostResource(Resource):
    """
    Resource to handle direct requests from a Host.
    The host's address is inferred from the falcon.Request.
    """

    def on_put(self, req, resp):
        """
        Handles the creation of a new Host.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        """
        try:
            address = req.env['REMOTE_ADDR']
        except KeyError:
            self.logger.info('Unable to determine host address')
            resp.status = falcon.HTTP_400
            return

        try:
            # Extract what we need from the input data.
            # Don't treat it as a skeletal host record.
            req_data = req.stream.read()
            req_body = json.loads(req_data.decode())
            ssh_priv_key = req_body['ssh_priv_key']
            # Remote user is optional.
            remote_user = req_body.get('remote_user', 'root')
            # Cluster member is optional.
            cluster_name = req_body.get('cluster', None)
        except (KeyError, ValueError):
            self.logger.info(
                'Bad client PUT request for host {0}: {1}'.
                format(address, req_data))
            resp.status = falcon.HTTP_400
            return

        resp.status, host_model = util.etcd_host_create(
            address, ssh_priv_key, remote_user, cluster_name)

        req.context['model'] = host_model
