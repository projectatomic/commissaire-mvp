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
import fnmatch
import importlib
import json
import logging
import logging.config
import os
import sys

import falcon

from commissaire import constants as C
from commissaire.compat.urlparser import urlparse
from commissaire.compat import exception
from commissaire.config import Config
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
        module = importlib.import_module(authentication_module_name)
        authentication_class = getattr(module, 'AuthenticationPlugin')
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

    # Special case:
    #
    # In the configuration file, the "register_store_handler" member
    # can be specified as a JSON object or a list of JSON objects.
    handler_key = 'register_store_handler'
    handler_list = json_object.get(handler_key)
    if type(handler_list) is dict:
        json_object[handler_key] = [handler_list]

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
        '--listen-interface', '-i', type=str, default='0.0.0.0',
        help='Interface to listen on')
    parser.add_argument(
        '--listen-port', '-p', type=int, default=8000,
        help='Port to listen on')
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
        metavar='MODULE_NAME',
        help=('Authentication Plugin module. '
              'EX: commissaire.authentication.httpbasicauth'))
    parser.add_argument(
        '--authentication-plugin-kwargs', type=str, default={},
        metavar='KEYWORD_ARGS',
        help='Authentication Plugin configuration (key=value,...)')
    parser.add_argument(
        '--register-store-handler', type=str, default=[],
        action='append', metavar='JSON_OBJECT',
        help='Store Handler configuration in JSON format, '
             'can be specified multiple times')

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


def register_store_handler(parser, store_manager, config):
    """
    Registers a new store handler type with a StoreHandlerManager.
    This function extracts and validates information required for
    registration from the configuration dictionary.

    :param parser: An argument parser
    :type parser: argparse.ArgumentParser
    :param store_manager: A store manager
    :type store_manager: commissaire.store.storehandlermanager.
                         StoreHandlerManager
    :param config: A configuration dictionary
    :type config: dict
    """
    # Import the handler class.
    try:
        module_name = config.pop('name')
    except KeyError:
        parser.error(
            'Store handler configuration missing "name" key: '
            '{}'.format(config))
    try:
        module = importlib.import_module(module_name)
        handler_type = getattr(module, 'StoreHandler')
    except ImportError:
        parser.error(
            'Invalid store handler module name: {}'.format(module_name))

    # Import the model classes.
    module = importlib.import_module('commissaire.handlers.models')
    available = {k: v for k, v in module.__dict__.items() if
                 isinstance(v, type) and issubclass(v, module.Model)}
    model_types = set()
    for pattern in config.pop('models', ['*']):
        matches = fnmatch.filter(available.keys(), pattern)
        if not matches:
            parser.error('No match for model: {}'.format(pattern))
        model_types.update([available[name] for name in matches])

    store_manager.register_store_handler(handler_type, config, *model_types)


def main():  # pragma: no cover
    """
    Main script entry point.
    """
    from commissaire.cherrypy_plugins.store import StorePlugin
    from commissaire.cherrypy_plugins.investigator import InvestigatorPlugin
    from commissaire.cherrypy_plugins.watcher import WatcherPlugin
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
        config.etcd['certificate_path'] = args.etcd_cert_path
        config.etcd['certificate_key_path'] = args.etcd_cert_key_path
        logging.info('Using client side certificate for etcd.')

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
        {"verify_location": args.tls_clientverifyfile}
    )

    if sys.version_info < (3, 0):
        from cherrypy.wsgiserver.wsgiserver2 import ssl_adapters
    else:
        from cherrypy.wsgiserver.wsgiserver3 import ssl_adapters
    ssl_adapters['builtin_client'] = new_ssl_adapter_cls

    server = cherrypy._cpserver.Server()
    server.socket_host = args.listen_interface
    server.socket_port = args.listen_port
    server.thread_pool = 10

    if bool(args.tls_keyfile) ^ bool(args.tls_certfile):
        parser.error(
            'Both a keyfile and certfile must be '
            'given for commissaire server TLS. Exiting ...')
    elif bool(args.tls_clientverifyfile) and not bool(args.tls_certfile):
        parser.error(
            'If a client verify file is given a TLS keyfile and '
            'certfile must be given as well. Exiting ...')

    if args.tls_keyfile and args.tls_certfile:
        server.ssl_module = 'builtin_client'
        server.ssl_certificate = args.tls_certfile
        server.ssl_private_key = args.tls_keyfile
        logging.info('Commissaire server TLS will be enabled.')
    server.subscribe()

    # Handle UNIX signals (SIGTERM, SIGHUP, SIGUSR1)
    if hasattr(cherrypy.engine, 'signal_handler'):
        cherrypy.engine.signal_handler.subscribe()

    # Configure the store plugin before starting it.
    store_plugin = StorePlugin(cherrypy.engine)
    store_manager = store_plugin.get_store_manager()

    # Configure store handlers from user data.
    #
    # FIXME The configuration format got too complicated to easily parse
    #       comma-separated key-value pairs so we punted and switched to
    #       JSON format. The authentication CLI options need reworked to
    #       keep the input formats consistent.
    if len(args.register_store_handler) == 0:
        # Order is significant; Kubernetes must be first.
        args.register_store_handler = [
            C.DEFAULT_KUBERNETES_STORE_HANDLER,
            C.DEFAULT_ETCD_STORE_HANDLER
        ]
    for config in args.register_store_handler:
        if type(config) is str:
            config = json.loads(config)
        if type(config) is dict:
            register_store_handler(parser, store_manager, config)
        else:
            parser.error(
                'Store handler format must be a JSON object, got a '
                '{} instead: {}'.format(type(config).__name__, config))

    # Add our plugins
    InvestigatorPlugin(cherrypy.engine).subscribe()
    WatcherPlugin(cherrypy.engine, store_manager.clone()).subscribe()

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
