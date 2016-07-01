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
Basic Model structure for commissaire.
"""

import copy
import json


class Model(object):
    """
    Parent class for models.
    """

    _json_type = None
    _attributes = ()
    _hidden_attributes = ()
    #: The primary way of looking up an instance
    _primary_key = None
    #: Defaults to use for attributes when calling new()
    _attribute_defaults = {}
    #: The attribute name which stores items if this is a list type
    _list_attr = None
    #: The class for items which will be stored in the list attribute
    _list_class = None

    def __init__(self, **kwargs):
        """
        Creates a new instance of a Model.

        :param kwargs: All keyword arguments to create the model.
        :type kwargs: dict
        :returns: The Model instance.
        :rtype: commissaire.model.Model
        """
        for key in self._attributes:
            if key not in kwargs:
                raise TypeError(
                    '__init__() missing 1 or more required '
                    'keyword arguments: {0}'.format(
                        ', '.join(self._attributes)))
            setattr(self, key, kwargs[key])

    @classmethod
    def new(cls, **kwargs):
        """
        Returns an instance with default values.

        :param kwargs: Any arguments explicitly set.
        :type kwargs: dict
        """
        instance = cls.__new__(cls)
        init_args = copy.deepcopy(cls._attribute_defaults)
        init_args.update(kwargs)
        instance.__init__(**init_args)
        return instance

    def _struct_for_json(self, secure=False):
        """
        Returns the proper structure for a model to be used in JSON.

        :param secure: If the structure needs to respect _hidden_attributes.
        :type secure: bool
        :returns: A dict or list depending
        :rtype: dict or list
        """
        if self._json_type is dict:
            return self._dict_for_json(secure)
        elif self._json_type is list:
            return self._list_for_json(secure)

    def _list_for_json(self, secure):
        """
        Returns a list structure of the data.

        :param secure: If the structure needs to respect _hidden_attributes.
        :type secure: bool
        :returns: A list of the data.
        :rtype: list
        """
        if len(self._attributes) == 1:
            data = getattr(self, self._attributes[0])
        return data

    def _dict_for_json(self, secure):
        """
        Returns a dict structure of the data.

        :param secure: If the structure needs to respect _hidden_attributes.
        :type secure: bool
        :returns: A dict of the data.
        :rtype: dict
        """
        data = {}
        for key in self._attributes:
            if secure:
                data[key] = getattr(self, key)
            elif key not in self._hidden_attributes:
                data[key] = getattr(self, key)
        return data

    def to_json(self, secure=False):
        """
        Returns a JSON representation of this model.

        :param secure: If the structure needs to respect _hidden_attributes.
        :type secure: bool
        :returns: The JSON representation.
        :rtype: str
        """
        return json.dumps(
            self._struct_for_json(secure=secure),
            default=lambda o: o._struct_for_json(secure=secure))
