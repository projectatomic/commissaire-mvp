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
Test cases for the commissaire.cherrypy_plugins.store module.
"""

import mock

from . import TestCase
from commissaire.cherrypy_plugins.store import Plugin
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_StorePlugin(TestCase):
    """
    Tests for the StorePlugin class.
    """

    #: Topics that should be registered
    topics = ('get-store-manager',)

    def before(self):
        """
        Called before every test.
        """
        self.bus = mock.MagicMock()
        self.plugin = Plugin(self.bus)

    def after(self):
        """
        Called after every test.
        """
        self.bus = None
        self.plugin = None

    def test_store_plugin_start(self):
        """
        Verify start() subscribes the proper topics.
        """
        self.plugin.start()
        # subscribe should be called a specific number of times
        self.assertEquals(len(self.topics), self.bus.subscribe.call_count)
        # Each subscription should have it's own call to register a callback
        for topic in self.topics:
            self.bus.subscribe.assert_any_call(topic, mock.ANY)

    def test_store_plugin_stop(self):
        """
        Verify stop() unsubscribes the proper topics.
        """
        self.plugin.stop()
        # unsubscribe should be called a specific number of times
        self.assertEquals(len(self.topics), self.bus.unsubscribe.call_count)
        # Each unsubscription should have it's own call
        # to deregister a callback
        for topic in self.topics:
            self.bus.unsubscribe.assert_any_call(topic, mock.ANY)

    def test_get_store_manager(self):
        """
        Verify get_store_manager returns a store manager.
        """
        manager = self.plugin.get_store_manager()
        self.assertIsInstance(manager, StoreHandlerManager)
