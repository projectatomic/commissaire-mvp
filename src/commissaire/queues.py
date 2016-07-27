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
All global queues.
"""

from commissaire.model import Model
from multiprocessing import Lock
from multiprocessing.queues import Empty
from multiprocessing.queues import Queue as MPQueue


class IterableModelQueue(MPQueue):
    """
    An iterable multiprocessing.queues.Queue that uses models and a cache for
    dequeue support.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes a new IterableModelQueue. See documentation on
        multiprocessing.queues.Queue

        :param args: All non-keyword arguments.
        :type args: list
        :param kwargs: All keyword arguments.
        :type kwargs: dict
        """
        MPQueue.__init__(self, *args, **kwargs)
        self._lock = Lock()
        self._cache = {}

    def __iter__(self):
        """
        Adds iterable support to multiprocessing.queues.Queue.
        """
        for item in self._cache.values():
            yield item
        raise StopIteration()

    def get(self, *args, **kwargs):
        """
        Returns an item off the queue and updates the cache. See documentation
        on multiprocessing.queues.Queue

        :param args: All non-keyword arguments.
        :type args: list
        :param kwargs: All keyword arguments.
        :type kwargs: dict
        :returns: The item off the queue.
        :rtype: mixed
        """
        item = super(IterableModelQueue, self).get(*args, **kwargs)
        item_model = self._get_obj_model(item)
        if item_model.primary_key in self._cache.keys():
            del self._cache[item_model.primary_key]
        return item

    def dequeue(self, obj):
        """
        Removes a specific item from the queue and cache.

        :param obj: The item to deque.
        :type obj:  commissaire.model.Model
        """
        with self._lock:
            obj_model = self._get_obj_model(obj)
            if obj_model.primary_key in self._cache.keys():
                try:
                    while True:
                            item = self.get_nowait()
                            item_model = self._get_obj_model(item)
                            if item_model.primary_key != obj_model.primary_key:
                                self.put(item)
                            else:
                                break
                except Empty:
                    pass

    def put(self, obj, *args, **kwargs):
        """
        Puts a new object on the queue.

        :param obj: The object to put on the queue.
        :type obj: any
        :param args: All other non-keyword arguments.
        :type args: list
        :param kwargs: All other keyword arguments.
        :type kwargs: dict
        """
        obj_model = self._get_obj_model(obj)
        for item in self:
            item_model = self._get_obj_model(item)
            if item_model.primary_key == obj_model.primary_key:
                return

        self._cache[obj_model.primary_key] = obj
        super(IterableModelQueue, self).put(obj)

    def _get_obj_model(self, item):
        """
        Attempts to return the model instance from the item.

        :param item: The item which hopefully contains a model.
        :type item: mixed
        :returns: The found model instance
        :rtype: commissaire.model.Model
        :raise: Exception
        """
        try:
            if issubclass(item.__class__, Model):
                return item
        except TypeError:
            # It's not a class...
            pass
        if hasattr(item, '__iter__'):
            for x in item:
                try:
                    if issubclass(x.__class__, Model):
                        return x
                except TypeError:
                    # Not a class
                    pass
        raise Exception('No model in {0}'.format(item))


INVESTIGATE_QUEUE = MPQueue()
"""
Input queue for the investigator thread(s).

:expects: (store_manager, address, ssh_priv_key, remote_user)
:type: multiprocessing.queues.Queues
"""


WATCHER_QUEUE = IterableModelQueue()
"""
Input queue for watcher thread(s).

:expects: (Host, utcnow)
:type: commissaire.queues.IterableQueue
"""
