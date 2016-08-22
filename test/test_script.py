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
Test cases for the commissaire.script module.
"""

import argparse
import errno
import etcd
import falcon
import mock
import os
import os.path
import sys

from . import TestCase
from commissaire import script
from commissaire.store import ConfigurationError
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_CreateApp(TestCase):
    """
    Tests for the create_app function.
    """

    def test_create_app(self):
        """
        Verify the application is created as expected.
        """
        with mock.patch('cherrypy.engine.publish') as _publish:
            _publish.return_value = [[[], etcd.EtcdKeyNotFound]]
            app = script.create_app(
                'commissaire.authentication.httpbasicauth',
                {'filepath': os.path.realpath('../conf/users.json')})
            self.assertTrue(isinstance(app, falcon.API))
            self.assertEquals(2, len(app._middleware))


class Test_ParseUri(TestCase):
    """
    Tests the parse_uri function.
    """

    def test_parse_uri(self):
        """
        Verify parse_uri properly parses URIs.
        """
        parsed = script.parse_uri('http://127.0.0.1:2379', 'test')
        self.assertEquals('127.0.0.1', parsed.hostname)
        self.assertEquals(2379, parsed.port)
        self.assertEquals('http', parsed.scheme)

        for x in ('http://127.0.0.1:', 'http://127.0.0.1', 'http://1:a', ''):
            self.assertRaises(Exception, script.parse_uri, x, 'test')


class Test_ConfigFile(TestCase):
    """
    Tests user configuration permutations.
    """

    def test_read_config_file(self):
        """
        Test the _read_config_file function.
        """

        # Check handling of register-store-handler.
        data = ('{'
                '  "register-store-handler": ['
                '    {"name": "commissaire.store.etcdstorehandler"}'
                '  ]'
                '}')
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=data)) as _open:
            namespace = script._read_config_file()
            self.assertIsInstance(namespace.register_store_handler, list)
        data = ('{'
                '  "register-store-handler": {'
                '    "name": "commissaire.store.etcdstorehandler"'
                '  }'
                '}')
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=data)) as _open:
            namespace = script._read_config_file()
            self.assertIsInstance(namespace.register_store_handler, list)

    def test_register_store_handler(self):
        """
        Test the register_store_handler function.
        """
        def override_parser_error(string):
            raise sys.exc_info()[0]

        parser = mock.MagicMock(argparse.ArgumentParser)
        parser.error = override_parser_error
        store_manager = mock.MagicMock(StoreHandlerManager)

        config = {}
        self.assertRaises(
            KeyError, script.register_store_handler,
            parser, store_manager, config)

        config = {'name': 'commissaire.bogus.module'}
        self.assertRaises(
            ImportError, script.register_store_handler,
            parser, store_manager, config)

        config = {
            'name': 'commissaire.store.etcdstorehandler',
            'models': ['Host*']
        }
        script.register_store_handler(parser, store_manager, config)
        models = store_manager.register_store_handler.call_args[0][2:]
        self.assertTrue(len(models) > 1)
        self.assertTrue(all(x.__name__.startswith('Host') for x in models))

        store_manager = StoreHandlerManager()

        # Note, this config is missing required info.
        config = {
            'name': 'commissaire.store.etcdstorehandler',
            'certificate-path': '/path/to/cert',
            'models': ['*']
        }
        self.assertRaises(
            ConfigurationError, script.register_store_handler,
            parser, store_manager, config)

        store_manager = StoreHandlerManager()

        # Catch model conflicts (TestModel assigned to both handlers)
        config = {
            'name': 'commissaire.store.etcdstorehandler',
            'models': ['*']
        }
        script.register_store_handler(parser, store_manager, config)
        config = {
            'name': 'commissaire.store.kubestorehandler',
            'models': ['Host']
        }
        self.assertRaises(
            ConfigurationError, script.register_store_handler,
            parser, store_manager, config)


class Test_ParseArgs(TestCase):
    """
    Tests the parse_args function.
    """

    config_data = ('{'
        '  "listen-interface": "127.0.0.1",'
        '  "listen-port": 8888'
        '}')

    bad_config_data = '["I am supposed to be a dictionary. :("]'

    auth_plugin_no_name = ('{'
        '  "authentication-plugin": {'
        '      "kwarg": [1, 2, 3]'
        '} }')

    auth_plugin = ('{'
        '  "authentication-plugin": {'
        '      "name": "test_module",'
        '      "kwarg": [1, 2, 3, 4]'
        '} }')

    def test_missing_config_file(self):
        """
        Verify behavior for missing config file.
        """
        sys.argv = ['', '--config-file', '/some/bogus/location']
        parser = argparse.ArgumentParser()
        with mock.patch('__builtin__.open') as _open:
            # Make sure no config file is opened.
            _open.side_effect = IOError(
                errno.ENOENT, os.strerror(errno.ENOENT))
            self.assertRaises(IOError, script.parse_args, parser)

    def test_config_file_format(self):
        """
        Verify bad config file format is caught.
        """
        sys.argv = ['']
        parser = argparse.ArgumentParser()
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=self.bad_config_data)
                ) as _open:
            self.assertRaises(TypeError, script.parse_args, parser)

    def test_auth_plugin_config(self):
        """
        Verify parsing of inline authentication-plugin config.
        """
        sys.argv = ['']
        parser = argparse.ArgumentParser()
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=self.auth_plugin_no_name)
                ) as _open:
            self.assertRaises(ValueError, script.parse_args, parser)

        parser = argparse.ArgumentParser()
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=self.auth_plugin)
                ) as _open:
            args = script.parse_args(parser)
        self.assertTrue(hasattr(args, 'authentication_plugin'))
        self.assertTrue(hasattr(args, 'authentication_plugin_kwargs'))
        self.assertEquals(args.authentication_plugin, 'test_module')
        self.assertEquals(
            args.authentication_plugin_kwargs,
            {'kwarg': [1, 2, 3, 4]})

    def test_arg_priority(self):
        """
        Verify command-line arguments shadow config file.
        """
        sys.argv = ['', '--listen-interface', '10.10.10.10']
        parser = argparse.ArgumentParser()
        with mock.patch('__builtin__.open',
                        mock.mock_open(read_data=self.config_data)) as _open:
            args = script.parse_args(parser)
        self.assertEquals(args.listen_interface, '10.10.10.10')
        self.assertEquals(args.listen_port, 8888)
