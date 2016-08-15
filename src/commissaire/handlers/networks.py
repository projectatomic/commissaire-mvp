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
Network(s) handlers.
"""

import json

import cherrypy
import falcon

from commissaire import constants as C
from commissaire.resource import Resource
from commissaire.handlers.models import Network, Networks
from commissaire.store.etcdstorehandler import EtcdStoreHandler


class NetworksResource(Resource):
    """
    Resource for working with Networks.
    """

    def on_get(self, req, resp):
        """
        Handles GET requests for Networks.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        """

        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            networks = store_manager.list(Networks(networks=[]))
            if len(networks.networks) == 0:
                raise Exception()
            resp.status = falcon.HTTP_200
            resp.body = json.dumps([
                network.name for network in networks.networks])
        except Exception:
            self.logger.warn(
                'Store does not have any networks. Returning [] and 404.')
            resp.status = falcon.HTTP_404
            req.context['model'] = None
            return


class NetworkResource(Resource):
    """
    Resource for working with a single Network.
    """

    def on_get(self, req, resp, name):
        """
        Handles retrieval of an existing Network.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param name: The friendly name of the network.
        :type address: str
        """
        try:
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            network = store_manager.get(Network.new(name=name))
            resp.status = falcon.HTTP_200
            req.context['model'] = network
        except:
            resp.status = falcon.HTTP_404
            return

    def on_put(self, req, resp, name):
        """
        Handles the creation of a new Network.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param name: The friendly name of the network.
        :type address: str
        """
        try:
            req_data = req.stream.read()
            req_body = json.loads(req_data.decode())
            network_type = req_body['type']
            options = req_body.get('options', {})
        except (KeyError, ValueError):
            self.logger.info(
                'Bad client PUT request for network {0}: {1}'.
                format(name, req_data))
            resp.status = falcon.HTTP_400
            return

        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        # If the type is flannel_etcd yet we have not etcd backend configured
        # don't create and notify the caller
        if network_type == C.NETWORK_TYPE_FLANNEL_ETCD:
            backend_found = False
            for handler_type, _, _ in store_manager.list_store_handlers():
                if handler_type is EtcdStoreHandler:
                    backend_found = True
                    break

            if not backend_found:
                self.logger.info(
                    'Network {0} can not be created as type flannel_etcd '
                    'as no etcd backend is configured.'.format(name))
                resp.status = falcon.HTTP_CONFLICT
                return

        network = Network.new(name=name, type=network_type, options=options)
        self.logger.debug('Saving network: {0}'.format(network.to_json()))
        store_manager.save(network)

        resp.status = falcon.HTTP_CREATED
        req.context['model'] = network

    def on_delete(self, req, resp, name):
        """
        Handles the Deletion of a Network.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :param name: The friendly name of the network.
        :type address: str
        """
        resp.body = '{}'
        store_manager = cherrypy.engine.publish('get-store-manager')[0]
        try:
            store_manager.delete(Network.new(name=name))
            resp.status = falcon.HTTP_200
        except Exception as error:
            self.logger.warn('{}: {}'.format(type(error), error))
            resp.status = falcon.HTTP_404
