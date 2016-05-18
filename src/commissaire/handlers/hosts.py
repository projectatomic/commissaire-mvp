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

import falcon

from commissaire.resource import Resource
from commissaire.handlers.models import Host, Hosts, Cluster, Clusters
import commissaire.handlers.util as util


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
            hosts = Hosts.retrieve()
            if len(hosts.hosts) == 0:
                raise Exception()
            resp.status = falcon.HTTP_200
            req.context['model'] = hosts
        except:
            # This was originally a "no content" but I think a 404 makes
            # more sense if there are no hosts
            self.logger.warn(
                'Etcd does not have any hosts. Returning [] and 404.')
            resp.status = falcon.HTTP_404
            req.context['model'] = None
            return


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
        # TODO: Verify input
        try:
            host = Host.retrieve(address)
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
        # TODO: Move to bus.publish
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
        try:
            Host.delete(address)
            resp.status = falcon.HTTP_200
        except:
            resp.status = falcon.HTTP_404

        # Also remove the host from all clusters.
        # Note: We've done all we need to for the host deletion,
        #       so if an error occurs from here just log it and
        #       return.
        try:
            clusters = Clusters.retrieve()
        except:
            self.logger.warn('Etcd does not have any clusters')
            return
        try:
            for cluster_name in clusters.clusters:
                self.logger.debug('Checking cluster {0}'.format(cluster_name))
                cluster = Cluster.retrieve(cluster_name)
                if address in cluster.hostset:
                    self.logger.info('Removing {0} from cluster {1}'.format(
                                     address, cluster_name))
                    cluster.hostset.remove(address)
                    cluster.save(cluster_name)
                    self.logger.info(
                        '{0} has been removed from cluster {1}'.format(
                            address, cluster_name))
        except:
            self.logger.warn('Failed to remove {0} from cluster {1}'.format(
                address, cluster_name))


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
        # TODO: Move this to bus.publish
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
