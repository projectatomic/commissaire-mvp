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
import re
import json


class ModelError(Exception):
    """
    Base exception class for Model errors.
    """
    pass


class ValidationError(ModelError):
    """
    Exception class for validation errors.
    """
    pass


class CoercionError(ModelError):
    """
    Exception class for coercion errors.
    """
    pass


class Model(object):
    """
    Parent class for models.
    """

    _json_type = None
    #: Dict of attribute_name->{type, regex}. Regex is optional.
    _attribute_map = {}
    #: Attributes which should only be shown if the render is 'secure'
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
        # self._attributes = self._attribute_map.keys()
        for key in self._attribute_map.keys():
            if key not in kwargs:
                raise TypeError(
                    '__init__() missing 1 or more required '
                    'keyword arguments: {0}'.format(
                        ', '.join(self._attribute_map.keys())))
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

    @property
    def primary_key(self):  # pragma: no cover
        """
        Shortcut property to get the value of the primary key.
        """
        return getattr(self, self._primary_key)

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
        if len(self._attribute_map.keys()) == 1:
            data = getattr(self, self._attribute_map.keys()[0])
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
        for key in self._attribute_map.keys():
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

    def _validate(self):
        """
        Validates the attribute data of the current instance.

        :raises: ValidationError
        """
        errors = []
        for attr, spec in self._attribute_map.items():
            value = getattr(self, attr)
            if not isinstance(value, spec['type']):
                errors.append(
                    '{0}.{1}: Expected type {2}. Got {3}'.format(
                        self.__class__.__name__, attr,
                        spec['type'], type(value)))

            try:
                if spec.get('regex') and not re.match(spec['regex'], value):
                    errors.append(
                        '{0}.{1}: Value did validate against the '
                        'provided regular expression "{2}"'.format(
                            self.__class__.__name__, attr, spec['regex']))
            except TypeError:
                errors.append(
                    '{0}.{1}: Value can not be validated by a '
                    'regular expression'.format(self.__class__.__name__, attr))

        if errors:
            raise ValidationError(
                '{0} instance is invalid due to {1} errors.'.format(
                    self.__class__.__name__, len(errors)), errors)

    def _coerce(self):
        """
        Attempts to force the typing set forth in _attribute_map.

        :raises: commissaire.model.CoercionError
        """
        errors = []
        for attr, spec in self._attribute_map.items():
            value = getattr(self, attr)
            if not isinstance(value, spec['type']):
                try:
                    caster = spec['type']
                    if spec['type'] is basestring:
                        caster = str

                    setattr(self, attr, caster(value))
                except Exception as ex:
                    errors.append(
                        '{0}.{1} can not be coerced from {2} to {3} '
                        'due to {4}: {5}'.format(
                            self.__class__.__name__, attr,
                            type(value), spec['type'], type(ex), ex))
        if errors:
            raise CoercionError(
                '{0} instance failed coercion due to {1} errors.'.format(
                    len(errors), errors))
