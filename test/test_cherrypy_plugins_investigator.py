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
Test cases for the commissaire.cherrypy_plugins.investigator module.
"""

import mock

from . import TestCase
from commissaire.cherrypy_plugins.investigator import Plugin


class Test_InvestigatorPlugin(TestCase):
    """
    Tests for the InvestigatorPlugin class.
    """

    #: Topics that should be registered
    topics = ('investigator-is-alive', )

    def before(self):
        """
        Called before every test.
        """
        self.bus = mock.MagicMock()
        self.plugin = Plugin(self.bus, {})

    def after(self):
        """
        Called after every test.
        """
        self.bus = None
        self.plugin = None

    def test_investigator_plugin_creation(self):
        """
        Verify that the creation of the plugin works as it should.
        """
        # The processes should not have started yet
        self.assertFalse(self.plugin.is_alive())

        # There should be bus subscribed topics
        for topic in self.topics:
            self.bus.subscribe.assert_any_call(topic, mock.ANY)

    def test_investigator_plugin_start(self):
        """
        Verify start() starts the background process.
        """
        self.assertFalse(self.plugin.is_alive())
        self.plugin.start()
        self.assertTrue(self.plugin.is_alive())
        self.plugin.stop()

    def test_investigator_plugin_stop(self):
        """
        Verify stop() unsubscribes topics.
        """
        self.plugin.start()
        self.plugin.stop()
        # unsubscribe should be called a specific number of times
        self.assertEquals(len(self.topics), self.bus.unsubscribe.call_count)
        # Each unsubscription should have it's own call
        # to deregister a callback
        for topic in self.topics:
            self.bus.unsubscribe.assert_any_call(topic, mock.ANY)
