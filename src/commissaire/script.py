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

import argparse
import cherrypy
import json
import logging
import logging.config
import os
import sys

import etcd
import falcon

from commissaire.compat.urlparser import urlparse
from commissaire.compat import exception
from commissaire.config import Config, cli_etcd_or_default
from commissaire.handlers.clusters import (
    ClustersResource, ClusterResource,
    ClusterHostsResource, ClusterSingleHostResource,
    ClusterDeployResource, ClusterRestartResource,
    ClusterUpgradeResource)
from commissaire.handlers.hosts import (
    HostCredsResource, HostsResource, HostResource, ImplicitHostResource)
from commissaire.handlers.status import StatusResource
from commissaire.middleware import JSONify
from commissaire.ssl_adapter import ClientCertBuiltinSSLAdapter

# XXX Temporary until we have a real storage plugin system.
from commissaire.model import Model as BogusModelType
from commissaire.store.etcdstoreplugin import EtcdStorePlugin


def create_app(
        authentication_module_name,
        authentication_kwargs):
    """
    Creates a new WSGI compliant commissaire application.

    :param authentication_module_name: Full name of the authentication module.
    :type authentication_module_name: str
    :param authentication_kwargs: Keyword arguments to pass to the auth mod.
    :type authentication_kwargs: dict
    :returns: The commissaire application.
    :rtype: falcon.API
    """
    try:
        authentication_class = getattr(__import__(
            authentication_module_name, fromlist=["True"]),
            'AuthenticationPlugin')
        authentication = authentication_class(**authentication_kwargs)
    except ImportError:
        raise Exception('Can not import {0} for authentication'.format(
            authentication_module_name))

    app = falcon.API(middleware=[authentication, JSONify()])

    app.add_route('/api/v0/status', StatusResource())
    app.add_route('/api/v0/cluster/{name}', ClusterResource())
    app.add_route(
        '/api/v0/cluster/{name}/hosts',
        ClusterHostsResource())
    app.add_route(
        '/api/v0/cluster/{name}/hosts/{address}',
        ClusterSingleHostResource())
    app.add_route(
        '/api/v0/cluster/{name}/deploy',
        ClusterDeployResource())
    app.add_route(
        '/api/v0/cluster/{name}/restart',
        ClusterRestartResource())
    app.add_route(
        '/api/v0/cluster/{name}/upgrade',
        ClusterUpgradeResource())
    app.add_route('/api/v0/clusters', ClustersResource())
    app.add_route('/api/v0/host', ImplicitHostResource())
    app.add_route('/api/v0/host/{address}', HostResource())
    app.add_route('/api/v0/host/{address}/creds', HostCredsResource())
    app.add_route('/api/v0/hosts', HostsResource())
    return app


def parse_uri(uri, name):
    """
    Parses and returns a parsed URI.

    :param uri: The URI to parse.
    :type uri: str
    :param name: The name to use for errors.
    :type name: str
    :returns: A parsed URI.
    :rtype: ParseResult
    :raises: Exception
    """
    parsed = urlparse(uri)
    # Verify we have what we need
    if not uri or None in (parsed.port, parsed.hostname, parsed.scheme):
        raise Exception(
            ('You must provide a full {0} URI. '
             'EX: http://127.0.0.1:2379'.format(name)))
    return parsed


def _read_config_file(path=None):
    """
    Attempts to parse a configuration file, formatted as a JSON object
    with member names matching documented command-line arguments.

    If a config file path is explicitly given, then failure to open the
    file will raise an IOError.  Otherwise a default path is tried, but
    no IOError is raised on failure.  If the file can be opened but not
    parsed, an exception is always raised.

    :param path: Full path to the config file, or None
    :type path: str or None
    :returns: A namespace object, possibly empty
    :rtype: argparse.Namespace
    """
    json_object = {}
    using_default = False

    if path is None:
        path = '/etc/commissaire/commissaire.conf'
        using_default = True

    try:
        with open(path, 'r') as fp:
            json_object = json.load(fp)
        # XXX Logging is not yet set up, so just print.
        if using_default:
            print('Using configuration in {0}'.format(path))
    except IOError:
        if not using_default:
            raise

    if type(json_object) is not dict:
        raise TypeError('{0}: '.format(path) +
                        'File content must be a JSON object')

    # Normalize member names by converting hypens to underscores.
    json_object = {k.replace('-', '_'): v for k, v in json_object.items()}

    # Special case:
    #
    # In the configuration file, the "authentication_plugin" member
    # can also be specified as a JSON object.  The object must have
    # at least a 'name' member specifying the plugin module name.
    auth_key = 'authentication_plugin'
    auth_plugin = json_object.get(auth_key)
    if type(auth_plugin) is dict:
        if 'name' not in auth_plugin:
            raise ValueError(
                '{0}: "{1}" is missing a "name" member'.format(
                    path, auth_key))
        json_object[auth_key] = auth_plugin.pop('name')
        json_object['authentication_plugin_kwargs'] = auth_plugin

    return argparse.Namespace(**json_object)


def parse_args(parser):
    """
    Parses and combines arguments from the server configuration file
    and the command-line invocation.  Command-line arguments override
    the configuration file.

    The 'parser' argument should be a fresh argparse.ArgumentParser
    instance with a suitable description, epilog, etc.  This method
    will add arguments to it.

    :param parser: An argument parser instance
    :type parser: argparse.ArgumentParser
    """
    # Do not use required=True because it would preclude such
    # arguments from being specified in a configuration file.
    # Instead we manually check for required arguments below.
    parser.add_argument(
        '--config-file', '-c', type=str,
        help='Full path to a JSON configuration file '
             '(command-line arguments override)')
    parser.add_argument(
        '--listen-interface', '-i', type=str,
        help='Interface to listen on')
    parser.add_argument(
        '--listen-port', '-p', type=int, help='Port to listen on')
    parser.add_argument(
        '--etcd-uri', '-e', type=str,
        help=('Full URI for etcd. This value is used for both local and remote'
              ' host node connections to etcd.'
              ' EX: http://192.168.152.100:2379'))
    parser.add_argument(
        '--etcd-cert-path', '-C', type=str,
        help='Full path to the client side certificate.')
    parser.add_argument(
        '--etcd-cert-key-path', '-K', type=str,
        help='Full path to the client side certificate key.')
    parser.add_argument(
        '--etcd-ca-path', '-A', type=str,
        help='Full path to the CA file.')
    parser.add_argument(
        '--kube-uri', '-k', type=str,
        help=('Full URI for kubernetes. This value is used for both local and'
              ' remote host node connection to kubernetes.'
              ' EX: http://192.168.152.101:8080'))
    parser.add_argument(
        '--tls-keyfile', type=str,
        help='Full path to the TLS keyfile for the commissaire server')
    parser.add_argument(
        '--tls-certfile', type=str,
        help='Full path to the TLS certfile for the commissaire server')
    parser.add_argument(
        '--tls-clientverifyfile', type=str, required=False,
        help='Full path to the TLS file containing the certificate '
             'authorities that client certificates should be verified against')
    parser.add_argument(
        '--authentication-plugin', type=str,
        default='commissaire.authentication.httpbasicauth',
        help=('Authentication Plugin module. '
              'EX: commissaire.authentication.httpbasicauth'))
    parser.add_argument(
        '--authentication-plugin-kwargs', type=str, default={},
        help='Authentication Plugin configuration (key=value)')

    # We have to parse the command-line arguments twice.  Once to extract
    # the --config-file option, and again with the config file content as
    # a baseline.
    args = parser.parse_args()
    namespace = _read_config_file(args.config_file)
    args = parser.parse_args(namespace=namespace)

    # Make sure required arguments are present.
    required_args = ('etcd_uri', 'kube_uri')
    missing_args = []
    for name in required_args:
        if getattr(args, name) is None:
            missing_args.append(name.replace('_', '-'))
    if missing_args:
        parser.error('Missing required arguments: {0}'.format(
            ', '.join(missing_args)))

    return args


def main():  # pragma: no cover
    """
    Main script entry point.
    """
    from commissaire.cherrypy_plugins.store import StorePlugin
    from commissaire.cherrypy_plugins.investigator import InvestigatorPlugin
    config = Config()

    epilog = ('Example: ./commissaire -e http://127.0.0.1:2379'
              ' -k http://127.0.0.1:8080')

    parser = argparse.ArgumentParser(epilog=epilog)

    try:
        args = parse_args(parser)
        config.etcd['uri'] = parse_uri(args.etcd_uri, 'etcd')
        config.kubernetes['uri'] = parse_uri(args.kube_uri, 'kube')
    except Exception:
        _, ex, _ = exception.raise_if_not(Exception)
        parser.error(ex)

    store_kwargs = {
        'read_timeout': 2,
        'host': config.etcd['uri'].hostname,
        'port': config.etcd['uri'].port,
        'protocol': config.etcd['uri'].scheme,
    }

    if bool(args.etcd_ca_path):
        config.etcd['certificate_ca_path'] = args.etcd_ca_path

    # We need all args to use a client side cert for etcd
    if bool(args.etcd_cert_path) ^ bool(args.etcd_cert_key_path):
        parser.error(
            'Both etcd-cert-path and etcd-cert-key-path must be '
            'provided to use a client side certificate with etcd.')
    elif bool(args.etcd_cert_path):
        if config.etcd['uri'].scheme != 'https':
            parser.error('An https URI is required when using '
                         'client side certificates.')
        store_kwargs['cert'] = (args.etcd_cert_path, args.etcd_cert_key_path)
        config.etcd['certificate_path'] = args.etcd_cert_path
        config.etcd['certificate_key_path'] = args.etcd_cert_key_path
        logging.info('Using client side certificate for etcd.')

    ds = etcd.Client(**store_kwargs)

    try:
        logging.config.dictConfig(
            json.loads(ds.read('/commissaire/config/logger').value))
        logging.info('Using Etcd for logging configuration.')
    except etcd.EtcdKeyNotFound:
        found_logger_config = False
        for logger_path in (
                '/etc/commissaire/logger.json', './conf/logger.json'):
            if os.path.isfile(logger_path):
                with open(logger_path, 'r') as logging_default_cfg:
                    logging.config.dictConfig(
                        json.loads(logging_default_cfg.read()))
                    found_logger_config = True
                logging.warn('No logger configuration in Etcd. Using defaults '
                             'at {0}'.format(logger_path))
        if not found_logger_config:
            parser.error(
                'Unable to find any logging configuration. Exiting ...')

    except etcd.EtcdConnectionFailed:
        _, ecf, _ = exception.raise_if_not(etcd.EtcdConnectionFailed)
        err = 'Unable to connect to Etcd: {0}. Exiting ...'.format(ecf)
        logging.fatal(err)
        parser.error('{0}\n'.format(err))
        raise SystemExit(1)

    # TLS options
    tls_keyfile = cli_etcd_or_default(
        'tlskeyfile', args.tls_keyfile, None, ds)
    tls_certfile = cli_etcd_or_default(
        'tlscertfile', args.tls_certfile, None, ds)
    tls_clientverifyfile = cli_etcd_or_default(
        'tls-clientverifyfile', args.tls_clientverifyfile, None, ds)

    interface = cli_etcd_or_default(
        'listeninterface', args.listen_interface, '0.0.0.0', ds)
    port = cli_etcd_or_default('listenport', args.listen_port, 8000, ds)

    # Pull options for accessing kubernetes
    try:
        config.kubernetes['token'] = ds.get(
            '/commissaire/config/kubetoken').value
        logging.info('Using kubetoken for kubernetes.')
    except etcd.EtcdKeyNotFound:
        logging.debug('No kubetoken set.')
    try:
        config.kubernetes['certificate_path'] = ds.get(
            '/commissaire/config/kube_certificate_path').value
        config.kubernetes['certificate_key_path'] = ds.get(
            '/commissaire/config/kube_certificate_key_path').value
        logging.info('Using client side certificate for kubernetes.')
    except etcd.EtcdKeyNotFound:
        logging.debug('No kubernetes client side certificate set.')

    # Add our config instance to the cherrypy global config so we can use it's
    # values elsewhere
    # TODO: Technically this should be in the cherrypy.request.app.config
    # but it looks like that isn't accessable with WSGI based apps
    cherrypy.config['commissaire.config'] = config

    logging.debug('Config: {0}'.format(config))

    cherrypy.server.unsubscribe()
    # Disable autoreloading and use our logger
    cherrypy.config.update({'log.screen': False,
                            'log.access_file': '',
                            'log.error_file': '',
                            'engine.autoreload.on': False})

    new_ssl_adapter_cls = type(
        "CustomClientCertBuiltinSSLAdapter",
        (ClientCertBuiltinSSLAdapter,),
        {"verify_location": tls_clientverifyfile}
    )

    if sys.version_info < (3, 0):
        from cherrypy.wsgiserver.wsgiserver2 import ssl_adapters
    else:
        from cherrypy.wsgiserver.wsgiserver3 import ssl_adapters
    ssl_adapters['builtin_client'] = new_ssl_adapter_cls

    server = cherrypy._cpserver.Server()
    server.socket_host = interface
    server.socket_port = int(port)
    server.thread_pool = 10

    if bool(tls_keyfile) ^ bool(tls_certfile):
        parser.error(
            'Both a keyfile and certfile must be '
            'given for commissaire server TLS. Exiting ...')
    elif bool(tls_clientverifyfile) and not bool(tls_certfile):
        parser.error(
            'If a client verify file is given a TLS keyfile and '
            'certfile must be given as well. Exiting ...')

    if tls_keyfile and tls_certfile:
        server.ssl_module = 'builtin_client'
        server.ssl_certificate = tls_certfile
        server.ssl_private_key = tls_keyfile
        logging.info('Commissaire server TLS will be enabled.')
    server.subscribe()

    # Handle UNIX signals (SIGTERM, SIGHUP, SIGUSR1)
    if hasattr(cherrypy.engine, 'signal_handler'):
        cherrypy.engine.signal_handler.subscribe()

    # Add our plugins
    InvestigatorPlugin(cherrypy.engine, config).subscribe()

    # Configure the store plugin before starting it.
    store_plugin = StorePlugin(cherrypy.engine)
    store_manager = store_plugin.get_store_manager()

    # XXX Temporary until we have a real storage plugin system.
    store_manager.register_store_handler(
        EtcdStorePlugin, store_kwargs, BogusModelType)

    store_plugin.subscribe()

    # NOTE: Anything that requires etcd should start AFTER
    # the engine is started
    cherrypy.engine.start()

    try:
        # Make and mount the app
        authentication_kwargs = {}
        if type(args.authentication_plugin_kwargs) is str:
            if '=' in args.authentication_plugin_kwargs:
                for item in args.authentication_plugin_kwargs.split(','):
                    key, value = item.split('=')
                    authentication_kwargs[key.strip()] = value.strip()
        elif type(args.authentication_plugin_kwargs) is dict:
            # _read_config_file() sets this up.
            authentication_kwargs = args.authentication_plugin_kwargs

        app = create_app(
            args.authentication_plugin,
            authentication_kwargs)
        cherrypy.tree.graft(app, "/")

        # Serve forever
        cherrypy.engine.block()
    except Exception:
        _, ex, _ = exception.raise_if_not(Exception)
        logging.fatal('Unable to start server: {0}'.format(ex))
        cherrypy.engine.stop()


if __name__ == '__main__':  # pragma: no cover
    main()
