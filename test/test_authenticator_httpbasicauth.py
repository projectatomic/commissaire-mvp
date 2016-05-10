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
Test cases for the commissaire.authentication.httpbasicauth module.
"""

import etcd
import falcon
import mock

from . import TestCase, get_fixture_file_path
from falcon.testing.helpers import create_environ
from commissaire.authentication import httpbasicauth
from commissaire.authentication import httpauthclientcert
from commissaire.ssl_adapter import SSL_CLIENT_VERIFY

class Test_HTTPBasicAuth(TestCase):
    """
    Tests for the _HTTPBasicAuth class.
    """

    def setUp(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        # Empty users dict prevents it from trying to load from etcd.
        self.http_basic_auth = httpbasicauth.HTTPBasicAuth(users={})

    def test_decode_basic_auth_with_header(self):
        """
        Verify decoding returns a filled tuple given the proper header no matter the case of basic.
        """
        basic = list('basic')
        for x in range(0, 5):
            headers = {'Authorization': '{0} YTph'.format(''.join(basic))}
            req = falcon.Request(
                create_environ(headers=headers))
            self.assertEquals(
                ('a', 'a'),
                self.http_basic_auth._decode_basic_auth(req))
            # Update the next letter to be capitalized
            basic[x] = basic[x].capitalize()

    def test_decode_basic_auth_with_bad_data_in_header(self):
        """
        Verify decoding returns no user with bad base64 data in the header.
        """
        req = falcon.Request(
            create_environ(headers={'Authorization': 'basic BADDATA'}))
        self.assertEquals(
            (None, None),
            self.http_basic_auth._decode_basic_auth(req))

    def test_decode_basic_auth_with_no_header(self):
        """
        Verify returns no user with no authorization header.
        """
        req = falcon.Request(create_environ(headers={}))
        self.assertEquals(
            (None, None),
            self.http_basic_auth._decode_basic_auth(req))


class TestHTTPBasicAuthByFile(TestCase):
    """
    Tests for the HTTPBasicAuth class using files.
    """

    def setUp(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        self.user_config = get_fixture_file_path('conf/users.json')
        self.http_basic_auth = httpbasicauth.HTTPBasicAuth(self.user_config)

    def test_load_with_non_parsable_file(self):
        """
        Verify load gracefully loads no users when the JSON file does not exist.
        """
        for bad_file in ('', get_fixture_file_path('test/bad.json')):
            self.http_basic_auth._data = {}
            self.http_basic_auth._load_from_file(bad_file)
            self.assertEquals(
                {},
                self.http_basic_auth._data
            )

    def test_authenticate_with_valid_user(self):
        """
        Verify authenticate works with a proper JSON file, Authorization header, and a matching user.
        """
        self.http_basic_auth = httpbasicauth.HTTPBasicAuth(self.user_config)
        req = falcon.Request(
            create_environ(headers={'Authorization': 'basic YTph'}))
        resp = falcon.Response()
        self.assertEquals(
            None,
            self.http_basic_auth.authenticate(req, resp))

    def test_authenticate_with_invalid_user(self):
        """
        Verify authenticate denies with a proper JSON file, Authorization header, and no matching user.
        """
        self.http_basic_auth = httpbasicauth.HTTPBasicAuth(self.user_config)
        req = falcon.Request(
            create_environ(headers={'Authorization': 'basic Yjpi'}))
        resp = falcon.Response()
        self.assertRaises(
            falcon.HTTPForbidden,
            self.http_basic_auth.authenticate,
            req, resp)

    def test_authenticate_with_invalid_password(self):
        """
        Verify authenticate denies with a proper JSON file, Authorization header, and the wrong password.
        """
        self.http_basic_auth= httpbasicauth.HTTPBasicAuth(self.user_config)
        req = falcon.Request(
            create_environ(headers={'Authorization': 'basic YTpiCg=='}))
        resp = falcon.Response()
        self.assertRaises(
            falcon.HTTPForbidden,
            self.http_basic_auth.authenticate,
            req, resp)


class TestHTTPBasicAuthByEtcd(TestCase):
    """
    Tests for the HTTPBasicAuth class using etcd.
    """

    def setUp(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        self.user_config = get_fixture_file_path('conf/users.json')

    def test_load_with_non_key(self):
        """
        Verify load raises when the key does not exist in etcd.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], etcd.EtcdKeyNotFound()]]

            self.assertRaises(
                etcd.EtcdKeyNotFound,
                httpbasicauth.HTTPBasicAuth)

    def test_load_with_bad_data(self):
        """
        Verify load raises when the data in Etcd is bad.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], ValueError()]]

            self.assertRaises(
                ValueError,
                httpbasicauth.HTTPBasicAuth)

    def test_authenticate_with_valid_user(self):
        """
        Verify authenticate works with a proper JSON in Etcd, Authorization header, and a matching user.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            # Mock the return of the Etcd get result
            return_value = mock.MagicMock(etcd.EtcdResult)
            with open(self.user_config, 'r') as users_file:
                return_value.value = users_file.read()

            _publish.return_value = [[return_value, None]]

            # Reload with the data from the mock'd Etcd
            http_basic_auth = httpbasicauth.HTTPBasicAuth()

            # Test the call
            req = falcon.Request(
                create_environ(headers={'Authorization': 'basic YTph'}))
            resp = falcon.Response()
            self.assertEquals(
                None,
                http_basic_auth.authenticate(req, resp))

    def test_authenticate_with_invalid_user(self):
        """
        Verify authenticate denies with a proper JSON in Etcd, Authorization header, and no matching user.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            # Mock the return of the Etcd get result
            return_value = mock.MagicMock(etcd.EtcdResult)
            with open(self.user_config, 'r') as users_file:
                return_value.value = users_file.read()
            _publish.return_value = [[return_value, None]]

            # Reload with the data from the mock'd Etcd
            http_basic_auth = httpbasicauth.HTTPBasicAuth()

            # Test the call
            req = falcon.Request(
                create_environ(headers={'Authorization': 'basic Yjpi'}))
            resp = falcon.Response()
            self.assertRaises(
                falcon.HTTPForbidden,
                http_basic_auth.authenticate,
                req, resp)

    def test_authenticate_with_invalid_password(self):
        """
        Verify authenticate denies with a proper JSON file, Authorization header, and the wrong password.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            return_value = mock.MagicMock(etcd.EtcdResult)
            with open(self.user_config, 'r') as users_file:
                return_value.value = users_file.read()
            _publish.return_value = [[return_value, None]]

            # Reload with the data from the mock'd Etcd
            http_basic_auth = httpbasicauth.HTTPBasicAuth()

            req = falcon.Request(
                create_environ(headers={'Authorization': 'basic YTpiCg=='}))
            resp = falcon.Response()
            self.assertRaises(
                falcon.HTTPForbidden,
                http_basic_auth.authenticate,
                req, resp)

class TestHTTPClientCertAuth(TestCase):
    """
    Tests for the HTTPBasicAuthByEtcd class.
    """

    def setUp(self):
        self.cert = {
            "version": 3,
            "notAfter": "Apr 11 08:32:52 2018 GMT",
            "notBefore": "Apr 11 08:32:51 2016 GMT",
            "serialNumber": "07",
            "subject": [
                [["organizationName", "system:master"]],
                [["commonName", "system:master-proxy"]]],
            "issuer": [
                [["commonName", "openshift-signer@1460363571"]]
             ]
        }

    def expect_forbidden(self, data=None, cn=None):
        auth = httpauthclientcert.HTTPClientCertAuth(cn=cn)
        req = falcon.Request(create_environ())
        if data is not None:
            req.env[SSL_CLIENT_VERIFY] = data

        resp = falcon.Response()
        self.assertRaises(
            falcon.HTTPForbidden,
            auth.authenticate,
            req, resp)

    def test_invalid_certs(self):
        """
        Verify authenticate denies when cert is missing or invalid
        """
        self.expect_forbidden()
        self.expect_forbidden(data={"bad": "data"})
        self.expect_forbidden(data={"subject": (("no", "cn"),)})


    def test_valid_certs(self):
        """
        Verify authenticate succeeds when cn matches, fails when it doesn't
        """
        self.expect_forbidden(data=self.cert, cn="other-cn")

        auth = httpauthclientcert.HTTPClientCertAuth(cn="system:master-proxy")
        req = falcon.Request(create_environ())
        req.env[SSL_CLIENT_VERIFY] = self.cert
        resp = falcon.Response()
        self.assertEqual(None, auth.authenticate(req, resp))

        # With no cn any is valid
        auth = httpauthclientcert.HTTPClientCertAuth()
        req = falcon.Request(create_environ())
        req.env[SSL_CLIENT_VERIFY] = self.cert
        resp = falcon.Response()
        self.assertEqual(None, auth.authenticate(req, resp))
