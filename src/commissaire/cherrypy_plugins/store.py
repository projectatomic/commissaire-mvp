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

from cherrypy.process import plugins

from commissaire.store.storehandlermanager import StoreHandlerManager


class StorePlugin(plugins.SimplePlugin):

    def __init__(self, bus):
        """
        Creates a new instance of the CherryPyStorePlugin.

        :param bus: The CherryPy bus.
        :type bus: cherrypy.process.wspbus.Bus
        """
        plugins.SimplePlugin.__init__(self, bus)
        self.manager = StoreHandlerManager()

    def start(self):
        """
        Starts the plugin.
        """
        self.bus.log('Starting up Store access')
        self.bus.subscribe('get-store-manager', self.get_store_manager)

    def stop(self):
        """
        Stops the plugin.
        """
        self.bus.log('Stopping down Store access')
        self.bus.unsubscribe('get-store-manager', self.get_store_manager)

    def get_store_manager(self):
        """
        :returns: The global StoreHandlerManager instance
        :rtype: commissaire.store.storehandlermanager.StoreHandlerManager
        """
        return self.manager


#: Generic name for the plugin
Plugin = StorePlugin
