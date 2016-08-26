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
from multiprocessing import Manager
from multiprocessing.queues import Empty

#: manager instance used in IterableModelQueues
manager = Manager()


class IterableModelQueue:
    """
    An iterable Queue like class that uses models and adds basic
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
        self._queue = manager.list()

    def __iter__(self):
        """
        Adds iterable support to multiprocessing.queues.Queue.
        """
        for item in self._queue:
            yield item
        raise StopIteration()

    def get(self, *args, **kwargs):
        """
        Returns an item off the queue. Arguments are ignored but accepted
        to keep a similar interface with Queue.

        :param args: All non-keyword arguments.
        :type args: list
        :param kwargs: All keyword arguments.
        :type kwargs: dict
        :returns: The item off the queue.
        :rtype: mixed
        """
        try:
            return self._queue.pop(0)
        except IndexError:
            raise Empty

    #: Forward function
    get_nowait = get

    def dequeue(self, obj):
        """
        Removes a specific item from the queue.

        :param obj: The item to deque.
        :type obj:  commissaire.model.Model
        """
        obj_model = self._get_obj_model(obj)
        for x in range(0, len(self._queue)):
            item = self._queue[x]
            # If the instance is a tuple snag the first element
            if isinstance(item, tuple):
                item = item[0]
            if obj_model.primary_key == item.primary_key:
                self._queue.pop(x)
                return

    def put(self, obj, *args, **kwargs):
        """
        Puts a new object on the queue. Arguments are ignored but accepted
        to keep a similar interface with Queue.

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
            # Don't add the items if it is already in the queue
            if item_model.primary_key == obj_model.primary_key:
                return
        self._queue.append(obj)

    #: See put
    put_nowait = put

    #: Forward function
    qsize = lambda s: len(s._queue)  # NOQA

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


WATCHER_QUEUE = IterableModelQueue()
"""
Input queue for watcher thread(s).

:expects: (Host, utcnow)
:type: commissaire.queues.IterableQueue
"""
