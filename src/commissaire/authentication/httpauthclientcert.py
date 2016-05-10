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


import falcon

from commissaire.authentication import Authenticator
from commissaire.ssl_adapter import SSL_CLIENT_VERIFY


class HTTPClientCertAuth(Authenticator):
    """
    Requires a client certificate. If a cn
    argument is given it must match the
    cn on any incoming certificate. If cn is
    left blank then client certificate is
    accepted.
    """

    def __init__(self, cn=None):
        self.cn = cn

    def authenticate(self, req, resp):
        cert = req.env.get(SSL_CLIENT_VERIFY, {})
        if cert:
            for obj in cert.get('subject', ()):
                for key, value in obj:
                    if key == 'commonName' and \
                            (not self.cn or value == self.cn):
                        return

        # Forbid by default
        raise falcon.HTTPForbidden('Forbidden', 'Forbidden')


AuthenticationPlugin = HTTPClientCertAuth
