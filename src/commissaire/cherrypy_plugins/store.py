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
Custom CherryPy plugins for commissaire.
"""

import logging
import sys

from cherrypy.process import plugins

from commissaire.store.storehandlermanager import StoreHandlerManager

# XXX Temporary until we have a real storage plugin system.
from commissaire.model import Model as BogusModelType
from commissaire.store.etcdstoreplugin import EtcdStorePlugin


class StorePlugin(plugins.SimplePlugin):

    def __init__(self, bus, store_kwargs):
        """
        Creates a new instance of the CherryPyStorePlugin.

        :param bus: The CherryPy bus.
        :type bus: cherrypy.process.wspbus.Bus
        :param store_kwargs: Keyword arguments used to make the Client.
        :type store_kwargs: dict
        """
        plugins.SimplePlugin.__init__(self, bus)
        self.logger = logging.getLogger('store')
        self.manager = StoreHandlerManager()

        # XXX Temporary until we have a real storage plugin system.
        self.manager.register_store_handler(
            EtcdStorePlugin, store_kwargs, BogusModelType)

    def start(self):
        """
        Starts the plugin.
        """
        self.bus.log('Starting up Store access')
        self.bus.subscribe("store-save", self.store_save)
        self.bus.subscribe("store-get", self.store_get)
        self.bus.subscribe("store-delete", self.store_delete)
        self.bus.subscribe("store-list", self.store_list)
        self.bus.subscribe("store-manager-clone", self.store_manager_clone)

    def stop(self):
        """
        Stops the plugin.
        """
        self.bus.log('Stopping down Store access')
        self.bus.unsubscribe("store-save", self.store_save)
        self.bus.unsubscribe("store-get", self.store_get)
        self.bus.unsubscribe("store-delete", self.store_delete)
        self.bus.unsubscribe("store-list", self.store_list)
        self.bus.unsubscribe("store-manager-clone", self.store_manager_clone)

    def store_save(self, key, json_entity, **kwargs):
        """
        Saves json to the store.

        :param key: The key to associate the data with.
        :type key: str
        :param json_entity: The json data to save.
        :type json_entity: str
        :param kwargs: All other keyword-args to pass to client
        :type kwargs: dict
        :returns: The stores response and any errors that may have occured
        :rtype: tuple(etcd.EtcdResult, Exception)
        """
        try:
            self.logger.debug('> SAVE {0} : {1}'.format(key, json_entity))
            response = self.manager.save(key, json_entity)
            self.logger.debug('< SAVE {0} : {1}'.format(key, response))
            return (response, None)
        except:
            _, exc, _ = sys.exc_info()
            return ([], exc)

    def store_get(self, key):
        """
        Retrieves json from the store.

        :param key: The key to associate the data with.
        :type key: str
        :returns: The stores response and any errors that may have occured
        :rtype: tuple(etcd.EtcdResult, Exception)
        """
        try:
            self.logger.debug('> GET {0}'.format(key))
            response = self.manager.get(key)
            self.logger.debug('< GET {0} : {1}'.format(key, response))
            return (response, None)
        except:
            _, exc, _ = sys.exc_info()
            return ([], exc)

    def store_delete(self, key):
        """
        Deletes json from the store.

        :param key: The key to associate the data with.
        :type key: str
        :returns: The stores response and any errors that may have occured
        :rtype: tuple(etcd.EtcdResult, Exception)
        """
        try:
            self.logger.debug('> DELETE {0}'.format(key))
            response = self.manager.delete(key)
            self.logger.debug('< DELETE {0} : {1}'.format(key, response))
            return (response, None)
        except:
            _, exc, _ = sys.exc_info()
            return ([], exc)

    def store_list(self, key):
        """
        Lists a directory.

        :param key: The key to associate the data with.
        :type key: str
        :returns: The stores response and any errors that may have occured
        :rtype: tuple(etcd.EtcdResult, Exception)
        """
        try:
            self.logger.debug('> LIST {0}'.format(key))
            response = self.manager.list(key)
            self.logger.debug('< LIST {0} : {1}'.format(key, response))
            return (response, None)
        except:
            _, exc, _ = sys.exc_info()
            return ([], exc)

    def store_manager_clone(self):
        """
        Creates a cloned instance of the configured StoreHandlerManager.

        :returns: A cloned StoreHandlerManager
        :rtype: commissaire.store.StoreHandlerManager
        """
        return self.manager.clone()


#: Generic name for the plugin
Plugin = StorePlugin
