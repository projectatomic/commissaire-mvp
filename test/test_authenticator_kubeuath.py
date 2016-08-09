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
Test cases for the commissaire.authentication.kubeauth module.
"""

import etcd
import falcon
import mock

from . import TestCase, get_fixture_file_path
from falcon.testing.helpers import create_environ
from commissaire.authentication import kubeauth
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_KubernetesAuth(TestCase):
    """
    Tests for the KubernetesAuth class.
    """

    def setUp(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            self._container_mgr = mock.MagicMock(
                'commissaire.store.kubestorehandler.KubernetesStoreHandler')
            _store_mgr = mock.MagicMock(list_container_managers=lambda s: self._container_mgr)
            _publish.return_value = [_store_mgr]

            self.kubernetes_auth = kubeauth.KubernetesAuth()

    def test_decode_bearer_auth_with_header(self):
        """
        Verify decoding returns a token given the proper header no matter the case of bearer.
        """
        bearer = list('bearer')
        for x in range(0, 5):
            headers = {'Authorization': '{0} 123'.format(''.join(bearer))}
            req = falcon.Request(
                create_environ(headers=headers))
            self.assertEquals(
                '123',
                self.kubernetes_auth._decode_bearer_auth(req))
            # Update the next letter to be capitalized
            bearer[x] = bearer[x].capitalize()

    def test_decode_bearer_auth_with_no_header(self):
        """
        Verify returns no user with no authorization header.
        """
        req = falcon.Request(create_environ(headers={}))
        self.assertEquals(
            None,
            self.kubernetes_auth._decode_bearer_auth(req))

    def test_authenticate_with_header(self):
        """
        Verify authenticate uses the submitted token and succeeds with the header.
        """
        self._container_mgr.__getitem__()._get = mock.MagicMock(
            return_value=mock.MagicMock(status_code=200))
        req = falcon.Request(create_environ(headers={'Authorization': 'Bearer 123'}))
        resp = falcon.Response()
        self.kubernetes_auth.authenticate(req, resp)
        self.assertEquals('200 OK', resp.status)

    def test_authenticate_with_header(self):
        """
        Verify authenticate uses the submitted token and forbids without the header.
        """
        self._container_mgr.__getitem__()._get = mock.MagicMock(
            return_value=mock.MagicMock(status_code=409))
        req = falcon.Request(create_environ(headers={}))
        resp = falcon.Response()
        self.assertRaises(
            falcon.errors.HTTPForbidden,
            self.kubernetes_auth.authenticate,
            req,
            resp)
