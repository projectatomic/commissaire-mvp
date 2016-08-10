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

import cherrypy
import falcon
import requests

from commissaire.authentication import Authenticator


class KubernetesAuth(Authenticator):
    """
    Kubernetes auth implementation of an authenticator.
    """

    def __init__(self, resource='/serviceaccounts'):
        """
        Creates an instance of the KubernetesAuth authenticator.

        :param resource: The Kubernetes resource to check against for auth.
        :type resource: str
        :raises: IndexError
        """
        try:
            self.resource_check = resource
            store_manager = cherrypy.engine.publish('get-store-manager')[0]
            self.logger.debug('{}'.format(store_manager))
            self._kubernetes = store_manager.list_container_managers(
                'kubernetes')[0]
        except IndexError as error:
            self.logger.fatal(
                'Unable to get the container manager for Kubernetes. Ensure '
                'that a store handler has been configured for kubernetes. '
                'Error: {0}: {1}'.format(type(error), error))
            raise error

    def _decode_bearer_auth(self, req):
        """
        Decodes basic auth from the header.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :returns: token or None if empty.
        :rtype: str
        """
        self.logger.debug('header: {}'.format(req.auth))
        if req.auth is not None:
            if req.auth.lower().startswith('bearer '):
                decoded = req.auth[7:]
                self.logger.debug('Token given: {0}'.format(decoded))
                return decoded
            else:
                self.logger.debug(
                    'Did not find bearer in the Authorization '
                    'header from {0}.'.format(req.remote_addr))
        # Default meaning no user or password
        self.logger.debug('Authentication for {0} failed.'.format(
            req.remote_addr))
        return None

    def authenticate(self, req, resp):
        """
        Implements the authentication logic.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :raises: falcon.HTTPForbidden
        """
        token = self._decode_bearer_auth(req)
        if token is not None:
            self.logger.debug('Token found: {0}'.format(token))
            try:
                # NOTE: We are assuming that if the user has access to
                # the resource they should be granted access to commissaire
                endpoint = self._kubernetes.base_uri + self.resource_check
                self.logger.debug('Checking against {0}.'.format(endpoint))
                resp = requests.get(
                    endpoint, headers={'Authentication': 'Bearer ' + token})
                self.logger.debug('Kubernetes response: {0}'.format(
                    resp.json()))
                # If we get a 200 then the user is valid. Anything else is
                # a failure
                if resp.status_code == 200:
                    self.logger.info(
                        'Accepted Kubernetes token for {0}'.format(
                            req.remote_addr))
                    return
                self.logger.debug('Rejecting Kubernetes token for {0}'.format(
                    req.remote_addr))
            except Exception as error:
                self.logger.warn(
                    'Encountered {0} while attempting to '
                    'authenticate. {1}'.format(type(error), error))
                raise error

        # Forbid by default
        raise falcon.HTTPForbidden('Forbidden', 'Forbidden')


AuthenticationPlugin = KubernetesAuth
