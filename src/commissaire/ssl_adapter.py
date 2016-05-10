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
"""

import ssl
import sys

from cherrypy import wsgiserver
from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter

SSL_CLIENT_VERIFY = "SSL_CLIENT_VERIFY"


class ClientCertBuiltinSSLAdapter(BuiltinSSLAdapter):
    """
    Forces use of SSLContext, so we can pass do
    client cerificate verification when required
    """

    def __init__(self, *args, **kwargs):
        super(ClientCertBuiltinSSLAdapter, self).__init__(*args, **kwargs)
        if not getattr(self, "context", None):
            self.context = ssl.create_default_context(
                purpose=ssl.Purpose.CLIENT_AUTH,
                cafile=self.certificate_chain
            )
            self.context.load_cert_chain(self.certificate, self.private_key)
        if getattr(self, "verify_location", None):
            self.context.load_verify_locations(self.verify_location)
            self.context.verify_mode = ssl.CERT_OPTIONAL

    def wrap(self, sock):
        """Forced to overide since older cherrypy versions don't support
           self.context. Once we require a version >= 3.2.3. This method
           can be removed.
        """
        try:
            s = self.context.wrap_socket(sock, do_handshake_on_connect=True,
                                         server_side=True)

        # Copied from cherrypy/wsgiserver/ssl_builtin.py.
        except ssl.SSLError:
            e = sys.exc_info()[1]
            if e.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it's connectable;
                # the 'ping' isn't SSL.
                return None, {}
            elif e.errno == ssl.SSL_ERROR_SSL:
                if e.args[1].endswith('http request'):
                    # The client is speaking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError
                elif e.args[1].endswith('unknown protocol'):
                    # The client is speaking some non-HTTP protocol.
                    # Drop the conn.
                    return None, {}
            raise
        return s, self.get_environ(s)

    def get_environ(self, sock):
        env = super(ClientCertBuiltinSSLAdapter, self).get_environ(sock)
        env[SSL_CLIENT_VERIFY] = sock.getpeercert()
        return env
