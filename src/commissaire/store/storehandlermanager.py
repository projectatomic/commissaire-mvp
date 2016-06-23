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


from copy import deepcopy

# XXX Temporary until we have a real storage plugin system.
from commissaire.model import Model as BogusModelType


class StoreHandlerManager(object):
    """
    Configures StoreHandler instances and routes storage requests to
    the appropriate instance.
    """

    def __init__(self):
        """
        Creates a new StoreHandlerManager instance.
        """
        self._registry = {}
        self._handlers = {}

        # XXX Temporary, until we're passing models instead of keys.
        self.bogus_model = BogusModelType()

    def clone(self):
        """
        Creates a copy of a StoreHandlerManager with the same configuration
        but no connections.
        """
        clone = StoreHandlerManager()
        clone._registry = deepcopy(self._registry)
        # clone._handlers should remain empty.
        return clone

    def register_store_handler(self, handler_type, config, *model_types):
        """
        Associates a StoreHandler subclass with one or more model types.

        :param handler_type: A class derived from StoreHandler
        :type handler_type: type
        :param config: Configuration parameters for the handler
        :type config: dict
        :param model_types: Model types under the handler's purview
        :type module_types: tuple
        """
        entry = (handler_type, config, model_types)
        self._registry.update({mt: entry for mt in model_types})

    def _get_handler(self, model):
        """
        Looks up, and if necessary instantiates, a StoreHandler instance
        for the given model.  Raises KeyError if no handler is registered
        for that type of model.
        """
        handler = self._handlers.get(type(model))
        if handler is None:
            # Let this raise a KeyError if the registry lookup fails.
            handler_type, config, model_types = self._registry[type(model)]
            handler = handler_type(config)
            self._handlers.update({mt: handler for mt in model_types})
        return handler

    def save(self, key, json_entity):
        """
        Saves data to a store and returns back a saved model.

        .. note::

           Eventually this method will take a model instance containing
           identifying information and data to save.  But for now this
           takes an etcd path and JSON string.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        handler = self._get_handler(self.bogus_model)
        return handler._save(key, json_entity)

    def get(self, key):
        """
        Returns data from a store and returns back a model.

        .. note::

           Eventually this method will take a model instance containing
           identifying information.  But for now this takes an etcd path.

        :param model_instance: Model instance to search and get
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        handler = self._get_handler(self.bogus_model)
        return handler._get(key)

    def delete(self, key):
        """
        Deletes data from a store.

        .. note::

           Eventually this method will take a model instance containing
           identifying information.  But for now this takes an etcd path.

        :param model_instance: Model instance to delete
        :type model_instance:
        """
        handler = self._get_handler(self.bogus_model)
        return handler._delete(key)

    def list(self, key):
        """
        Lists data at a location in a store and returns back model instances.

        .. note::

           Eventually this method will take a model instance containing
           identifying information.  But for now this takes an etcd path.

        :param model_instance: Model instance to search for and list
        :type model_instance: commissaire.model.Model
        :returns: A list of models
        :rtype: list
        """
        handler = self._get_handler(self.bogus_model)
        return handler._list(key)
