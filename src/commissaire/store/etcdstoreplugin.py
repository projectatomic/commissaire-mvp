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


import etcd

from commissaire.store import StoreHandlerBase


class EtcdStorePlugin(StoreHandlerBase):
    """
    Handler for data storage on etcd.
    """

    def __init__(self, config):
        """
        Creates a new instance of EtcdStorePlugin.

        :param config: Configuration details
        :type config: dict
        """
        self._store = etcd.Client(**config)

    def _save(self, key, json_entity):
        """
        Saves data to etcd and returns back a saved model.

        .. note::

           Eventually this method will take a model instance containing
           identifying information and data to save.  But for now this
           takes an etcd path and JSON string.

        :param model_instance: Model instance to save
        :type model_instance: commissaire.model.Model
        :returns: The saved model instance
        :rtype: commissaire.model.Model
        """
        return self._store.write(key, json_entity)

    def _get(self, key):
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
        return self._store.get(key)

    def _delete(self, key):
        """
        Deletes data from a store.

        .. note::

           Eventually this method will take a model instance containing
           identifying information.  But for now this takes an etcd path.

        :param model_instance: Model instance to delete
        :type model_instance:
        """
        return self._store.delete(key)

    def _list(self, key):
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
        return self._store.read(key, recursive=True)


StoreHandler = EtcdStorePlugin
