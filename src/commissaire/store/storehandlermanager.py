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

from commissaire.model import ValidationError


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

        self._container_managers = []

        # Logger objects can't be pickled, so fetch ours lazily so
        # cloned StoreHandlerManagers can be passed to subprocesses.
        self.__logger = None

    def clone(self):
        """
        Creates a copy of a StoreHandlerManager with the same configuration
        but no connections.
        """
        clone = StoreHandlerManager()
        clone._registry = deepcopy(self._registry)
        # clone._handlers should remain empty.
        # clone._container_managers should remain empty.
        # clone.__loggers should remain None.
        return clone

    def register_store_handler(self, handler_type, config, *model_types):
        """
        Associates a StoreHandler subclass with one or more model types.
        This will raise a ConfigurationError if any configuration parameters
        are invalid.

        :param handler_type: A class derived from StoreHandler
        :type handler_type: type
        :param config: Configuration parameters for the handler
        :type config: dict
        :param model_types: Model types under the handler's purview
        :type module_types: tuple
        """
        handler_type.check_config(config)
        entry = (handler_type, config, model_types)
        self._registry.update({mt: entry for mt in model_types})

    def list_store_handlers(self):
        """
        Returns all registered store handlers as a list of triples.
        Each triple resembles the register_store_handler() parameters:
        (handler_type, config, tuple_of_model_types)

        :returns: List of registered store handlers
        :rtype: list
        """
        # This collects all unique instances from the registry.
        return {id(x): x for x in self._registry.values()}.values()

    def list_container_managers(self, cluster_type=None):
        """
        Returns a list of container manager instances based on the
        registered store handler types and associated configuration.
        If cluster_type is given, restrict the list to managers for
        that type of cluster.

        :param cluster_type: Cluster type constant
        :type cluster_type: str
        :returns: List of container managers
        :rtype: list
        """
        if not self._container_managers:
            # Instantiate all container managers.
            for handler_type, config, _ in self.list_store_handlers():
                container_manager_class = getattr(
                    handler_type, 'container_manager_class')
                if container_manager_class:
                    # XXX Limit one container manager for now.
                    if not self._container_managers:
                        container_manager = container_manager_class(config)
                        self._container_managers.append(container_manager)
                    else:
                        logger = self._get_logger()
                        logger.warn(
                            'A container manager is already established, '
                            'skipping {0} as configured for store handler '
                            '"{1}"'.format(
                                container_manager_class.__name__,
                                handler_type.__name__))

        if cluster_type:
            result = [x for x in self._container_managers
                      if x.cluster_type == cluster_type]
        else:
            result = list(self._container_managers)

        return result

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
        handler = self._get_handler(model_instance)
        # Validate before saving
        try:
            model_instance._validate()
        except ValidationError as ve:
            logger.error(ve.args[0], ve.args[1])
            raise ve
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
        handler = self._get_handler(model_instance)
        logger.debug('> GET {0}'.format(model_instance))
        model_instance = handler._get(model_instance)
        # Validate after getting
        try:
            model_instance._validate()
        except ValidationError as ve:
            logger.error(ve.args[0], ve.args[1])
            raise ve
        logger.debug('< GET {0}'.format(model_instance))
        return model_instance

    def delete(self, model_instance):
        """
        Deletes data from a store.

        :param model_instance: Model instance to delete
        :type model_instance:
        """
        logger = self._get_logger()
        handler = self._get_handler(model_instance)
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
        handler = self._get_handler(model_instance)
        logger.debug('> LIST {0}'.format(model_instance))
        model_instance = handler._list(model_instance)
        logger.debug('< LIST {0}'.format(model_instance))
        return model_instance
