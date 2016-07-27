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
Watcher plugin which allows control of watcher via the wsbus.
"""

import os

from cherrypy.process import plugins

from multiprocessing import Process
from commissaire.queues import WATCHER_QUEUE
from commissaire.jobs.watcher import watcher


class WatcherPlugin(plugins.SimplePlugin):

    def __init__(self, bus, store_manager):
        """
        Creates a new instance of the WatcherPlugin.

        :param bus: The CherryPy bus.
        :type bus: cherrypy.process.wspbus.Bus
        :param store_manager: Proxy object for remtote stores
        :type store_manager: commissaire.store.StoreHandlerManager
        """
        plugins.SimplePlugin.__init__(self, bus)
        # multiprocessing.Process() uses fork() to execute the target
        # function.  That means the child process inherits the entire
        # state of the main process, this plugin included.
        #
        # When this process is forked, self.process will be a valid
        # Process object but self.process in the child process will
        # not.  We capture our own PID up front so the we can later
        # distinguish whether we're the parent or child process and
        # avoid interacting with an invalid Process object.
        self.main_pid = os.getpid()
        self.process = Process(
            target=watcher,
            args=(WATCHER_QUEUE, store_manager.clone()))
        # TODO: Move to start()
        self.bus.subscribe('watcher-is-alive', self.is_alive)

    def start(self):
        """
        Starts the plugin and the watchergator process.
        """
        self.bus.log('Starting up Watcher plugin')
        self.process.start()

    def stop(self):
        """
        Stops the plugin.
        """
        self.bus.log('Stopping down Watcher plugin')
        self.bus.unsubscribe('watcher-is-alive', self.is_alive)
        if os.getpid() == self.main_pid:
            self.process.terminate()
            self.process.join()

    def is_alive(self):
        """
        Returns whether the watcher process object is alive.

        The watcher process object is alive from the moment the
        start() method returns until the child process terminates.

        :returns: Whether the watcher is alive
        :rtype: bool
        """
        return self.process.is_alive()


#: Generic name for the plugin
Plugin = WatcherPlugin
