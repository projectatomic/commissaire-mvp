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
Investigator plugin which allows control of investigators via the wsbus.
"""

import os

from cherrypy.process import plugins

from multiprocessing import Process, Queue
from threading import Thread
from commissaire.jobs.investigator import investigator


class Sentinel(object):
    """
    Passed over a multiprocessing.Queue as a loop terminator.
    """
    pass


class InvestigatorPlugin(plugins.SimplePlugin):

    def __init__(self, bus):
        """
        Creates a new instance of the InvestigatorPlugin.

        :param bus: The CherryPy bus.
        :type bus: cherrypy.process.wspbus.Bus
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
        self.request_queue = Queue()
        self.response_queue = Queue()
        self.process = Process(
            target=investigator,
            args=(self.request_queue, self.response_queue))
        self.response_thread = None
        self.pending_requests = {}  # host address -> closure
        self.sentinel = Sentinel()  # stops the response thread

    def __response_thread(self):
        """
        Helper thread runs while the plugin is started.  It waits for
        completion responses from the investigator process, matches them
        to a pending requests table, and invokes a user-provided callback
        function.
        """
        while True:
            response = self.response_queue.get()
            assert os.getpid() == self.main_pid
            if isinstance(response, Sentinel):
                break
            host, exception = response
            try:
                closure = self.pending_requests.pop(host.address)
            except KeyError:
                self.bus.log(
                    'Unmatched investigator response '
                    'for host {0}'.format(host.address))
                continue
            self.bus.log(
                'Investigator response for host {0}: {1}'.format(
                    host.address, exception if exception else 'success!'))
            if callable(closure):
                closure(host, exception)

    def start(self):
        """
        Starts the plugin and the investigator process.
        """
        self.bus.log('Starting up Investigator plugin')
        self.bus.subscribe('investigator-is-alive', self.is_alive)
        self.bus.subscribe('investigator-is-pending', self.is_pending)
        self.bus.subscribe('investigator-submit', self.submit)
        self.response_thread = Thread(target=self.__response_thread)
        self.response_thread.start()
        self.process.start()

    def stop(self):
        """
        Stops the plugin.
        """
        self.bus.log('Stopping down Investigator plugin')
        self.bus.unsubscribe('investigator-is-alive', self.is_alive)
        self.bus.unsubscribe('investigator-is-pending', self.is_pending)
        self.bus.unsubscribe('investigator-submit', self.submit)
        if os.getpid() == self.main_pid:
            if self.response_thread:
                self.response_queue.put(self.sentinel)
                self.response_thread.join()
                self.response_thread = None
            self.process.terminate()
            self.process.join()

    def submit(self, store_manager, host, cluster, callback=None):
        """
        Submits a new request to the investigator process.  If a callback
        was given, it will be invoked when the request has finished.  The
        callback arguments are (store_manager, host, exception).  If the
        request is successful, the exception argument will be None.

        :param store_manager: A store manager (will be cloned)
        :type store_manager: commissaire.store.storehandlermanager.
                             StoreHandlerManager
        :param host: A Host model representing the host to investigate.
        :type host: commissaire.handlers.models.Host
        :param cluster: Cluster model instance the host is to be added to
        :type cluster: commissaire.handlers.models.Cluster or None
        :param callback: A callable to invoke when the request is complete.
        :type callback: callable or None
        """
        def invoke_callback(new_host, exception):
            callback(store_manager, new_host, exception)

        closure = invoke_callback if callback is not None else None
        self.pending_requests[host.address] = closure
        manager_clone = store_manager.clone()

        # Since cluster might be None we need to check for __dict__
        cluster_dict = getattr(cluster, '__dict__', None)

        job_request = (manager_clone, host.__dict__, cluster_dict)
        self.request_queue.put(job_request)

    def is_alive(self):
        """
        Returns whether the investigator process object is alive.

        The investigator process object is alive from the moment the
        start() method returns until the child process terminates.

        :returns: Whether the investigator is alive
        :rtype: bool
        """
        return self.process.is_alive()

    def is_pending(self, address):
        """
        Returns whether a request is pending for the given host address.

        :param address: Host address
        :type address: str
        """
        return address in self.pending_requests


#: Generic name for the plugin
Plugin = InvestigatorPlugin
