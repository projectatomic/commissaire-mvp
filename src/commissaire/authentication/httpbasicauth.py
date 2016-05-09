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
import json

from commissaire.authentication import Authenticator
from commissaire.compat import exception
from commissaire.compat.b64 import base64


class HTTPBasicAuth(Authenticator):
    """
    Basic auth implementation of an authenticator.
    """

    def __init__(self, filepath=None, users=None):
        """
        Creates an instance of the HTTPBasicAuth authenticator.

        If a 'filepath' is specified, the file's content is loaded and, if
        applicable, merged into the 'users' dictionary.  If no arguments are
        given, the instance attempts to retrieve user passwords from etcd.

        :param filepath: Path to a JSON file containing hashed passwords
        :type filepath: str or None
        :param users: A dictionary of user names and hashed passwords, or None
        :type users: dict or None
        :returns: HTTPBasicAuth
        """
        self._data = {} if users is None else users
        if filepath is not None:
            self._load_from_file(filepath)
        elif users is None:
            self._load_from_etcd()

    def _load_from_etcd(self):
        """
        Loads authentication information from etcd.
        """
        d, error = cherrypy.engine.publish(
            'store-get', '/commissaire/config/httpbasicauthbyuserlist')[0]

        if error:
            if type(error) == ValueError:
                self.logger.warn(
                    'User configuration in Etcd is not valid JSON. Raising...')
            else:
                self.logger.warn(
                    'User configuration not found in Etcd. Raising...')
            self._data = {}
            raise error

        self._data = json.loads(d.value)
        self.logger.info('Loaded authentication data from Etcd.')

    def _load_from_file(self, path):
        """
        Loads authentication information from a JSON file.

        :param path: Path to the JSON file
        :type path: str
        """
        try:
            with open(path, 'r') as afile:
                self._data.update(json.load(afile))
                self.logger.info('Loaded authentication data from local file.')
        except:
            _, ve, _ = exception.raise_if_not((ValueError, IOError))
            self.logger.warn(
                'Denying all access due to problem parsing '
                'JSON file: {0}'.format(ve))

    def _decode_basic_auth(self, req):
        """
        Decodes basic auth from the header.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :returns: tuple -- (username, passphrase) or (None, None) if empty.
        :rtype: tuple
        """
        if req.auth is not None:
            if req.auth.lower().startswith('basic '):
                try:
                    decoded = tuple(base64.decodebytes(
                        req.auth[6:].encode('utf-8')).decode().split(':'))
                    self.logger.debug('Credentials given: {0}'.format(decoded))
                    return decoded
                except base64.binascii.Error:
                    self.logger.info(
                        'Bad base64 data sent. Setting to no user/pass.')
        # Default meaning no user or password
        return (None, None)

    def check_authentication(self, user, passwd):
        """
        Checks the user name and password from an Authorization header
        against the loaded datastore.

        :param user: User nane
        :type user: string
        :param passwd: Password
        :type passwd: string
        :returns: Whether access is granted
        :rtype: bool
        """
        import bcrypt

        valid = False
        hashed = self._data[user]['hash'].encode('utf-8')
        try:
            if bcrypt.hashpw(passwd.encode('utf-8'), hashed) == hashed:
                self.logger.debug(
                    'The provided hash for user {0} '
                    'matched: {1}'.format(user, passwd))
                valid = True
        except ValueError:
            pass  # Bad salt

        return valid

    def authenticate(self, req, resp):
        """
        Implements the authentication logic.

        :param req: Request instance that will be passed through.
        :type req: falcon.Request
        :param resp: Response instance that will be passed through.
        :type resp: falcon.Response
        :raises: falcon.HTTPForbidden
        """
        user, passwd = self._decode_basic_auth(req)
        if user is not None and passwd is not None:
            if user in self._data.keys():
                self.logger.debug('User {0} found in datastore.'.format(user))
                if self.check_authentication(user, passwd):
                    return  # Authentication is good

        # Forbid by default
        raise falcon.HTTPForbidden('Forbidden', 'Forbidden')


AuthenticationPlugin = HTTPBasicAuth
