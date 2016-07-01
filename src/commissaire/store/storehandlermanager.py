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

import logging

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

        # Logger objects can't be pickled, so fetch ours lazily so
        # cloned StoreHandlerManagers can be passed to subprocesses.
        self.__logger = None

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
        # clone.__loggers should remain None.
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

    def _get_logger(self):
        """
        Returns the 'store' logger for debug messages.

        :returns: Logger
        :rtype: logging.Logger
        """
        if self.__logger is None:
            self.__logger = logging.getLogger('store')
        return self.__logger

    def save(self, model_instance):
        """
        Saves data to a store and returns back a saved model.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        logger = self._get_logger()
        handler = self._get_handler(self.bogus_model)
        logger.debug('> SAVE {0}'.format(model_instance))
        model_instance = handler._save(model_instance)
        logger.debug('< SAVE {0}'.format(model_instance))
        return model_instance

    def get(self, model_instance):
        """
        Returns data from a store and returns back a model.

        :param model_instance: Model instance to search and get
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        logger = self._get_logger()
        handler = self._get_handler(self.bogus_model)
        logger.debug('> GET {0}'.format(model_instance))
        model_instance = handler._get(model_instance)
        logger.debug('< GET {0}'.format(model_instance))
        return model_instance

    def delete(self, model_instance):
        """
        Deletes data from a store.

        :param model_instance: Model instance to delete
        :type model_instance:
        """
        logger = self._get_logger()
        handler = self._get_handler(self.bogus_model)
        logger.debug('> DELETE {0}'.format(model_instance))
        handler._delete(model_instance)

    def list(self, model_instance):
        """
        Lists data at a location in a store and returns back model instances.

        :param model_instance: Model instance to search for and list
        :type model_instance: commissaire.model.Model
        :returns: A list of models
        :rtype: list
        """
        logger = self._get_logger()
        handler = self._get_handler(self.bogus_model)
        logger.debug('> LIST {0}'.format(model_instance))
        model_instance = handler._list(model_instance)
        logger.debug('< LIST {0}'.format(model_instance))
        return model_instance
