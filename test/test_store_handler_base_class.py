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
Test cases for the commissaire.store.StoreHandlerBase class.
"""

from . import TestCase
from commissaire.store import StoreHandlerBase


class _Test_StoreHandler(TestCase):
    """
    Tests for the StoreHandler class.
    """

    cls = None
    # (method_name, nargs)
    expected_methods = (
        ('_get_connection', 0),
        ('_save', 1),
        ('_get', 1),
        ('_delete', 1),
        ('_list', 1),
    )

    def before(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        self.instance = self.cls({})

    def test_expected_methods_exist(self):
        """
        Verify all StoreHandler expected methods are implemented.
        """
        for meth in self.expected_methods:
            self.assertTrue(getattr(self.instance, meth[0]))


class Test_StoreHandlerBaseClass(_Test_StoreHandler):
    """
    Tests for the StoreHandlerBase class.
    """

    cls = StoreHandlerBase

    def test_store_handler_base_methods(self):
        """
        Verify StoreHandlerBase base methods all raises.
        """
        for meth, nargs in self.expected_methods:
            self.assertRaises(
                NotImplementedError,
                getattr(self.instance, meth),
                *tuple(range(nargs)))
