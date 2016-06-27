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
Test cases for the commissaire.store.StoreHandlerManager class.
"""

import mock

from . import TestCase

from commissaire.model import Model as BogusModelType
from commissaire.store import StoreHandlerBase
from commissaire.store.storehandlermanager import StoreHandlerManager


class Test_StoreHandlerManager(TestCase):
    """
    Tests for the StoreHandlerManager class.
    """

    def test_storehandlermanager_initialization(self):
        """
        Verify the creation of a new StoreHandlerManager.
        """
        manager = StoreHandlerManager()
        # There all internal data should be empty
        self.assertEqual({}, manager._registry)
        self.assertEqual({}, manager._handlers)

    def test_storehandlermanager_clone(self):
        """
        Verify the StoreHandlerManager clone method works as expected.
        """
        manager = StoreHandlerManager()
        manager._registry['test'] = BogusModelType
        clone_result = manager.clone()
        # The manager and the cloned_result should not be the same
        self.assertNotEqual(manager, clone_result)
        # But their content should be
        self.assertEqual(manager._registry, clone_result._registry)
        # And the handlers should still be empty
        self.assertEqual({}, manager._handlers)

    def test_storehandlermanager_get(self):
        """
        Verify the StoreHandlerManager get method works as expected.
        """
        StoreHandlerBase = mock.MagicMock('StoreHandlerBase')
        StoreHandlerBase()._get.return_value = BogusModelType()
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        key = '/test'
        result = manager.get(key)
        StoreHandlerBase()._get.assert_called_once_with(key)
        self.assertEqual(StoreHandlerBase()._get.return_value, result)

    def test_storehandlermanager_delete(self):
        """
        Verify the StoreHandlerManager delete method works as expected.
        """
        StoreHandlerBase = mock.MagicMock('StoreHandlerBase')
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        key = '/test'
        manager.delete(key)
        StoreHandlerBase()._delete.assert_called_once_with(key)

    def test_storehandlermanager_save(self):
        """
        Verify the StoreHandlerManager save method works as expected.
        """
        StoreHandlerBase = mock.MagicMock('StoreHandlerBase')
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        key = '/test'
        value = {'test': 'data'}
        model_instance = BogusModelType()
        manager.save(model_instance)
        StoreHandlerBase()._save.assert_called_once_with(model_instance)

    def test_storehandlermanager_list(self):
        """
        Verify the StoreHandlerManager list method works as expected.
        """
        StoreHandlerBase = mock.MagicMock('StoreHandlerBase')
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        key = '/test'
        manager.list(key)
        StoreHandlerBase()._list.assert_called_once_with(key)

    def test_storehandlermanager_register_store_handler_with_one_model(self):
        """
        Verify StoreHandlerManager registers StoreHandlers properly with one model.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        expected = {
            BogusModelType: (StoreHandlerBase, {}, (BogusModelType, )),
        }
        self.assertEqual(expected, manager._registry)

    def test_storehandlermanager_register_store_handler_with_multiple_models(self):
        """
        Verify StoreHandlerManager registers StoreHandlers properly with multiple models.
        """
        # Set up a few more bogus classes for testing
        class BogusStoreHandler(StoreHandlerBase):
            pass

        class AnotherBogusModelType(BogusModelType):
            pass

        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        manager.register_store_handler(BogusStoreHandler, {}, AnotherBogusModelType)

        expected = {
            BogusModelType: (StoreHandlerBase, {}, (BogusModelType, )),
            AnotherBogusModelType: (BogusStoreHandler, {}, (AnotherBogusModelType, )),
        }

        self.assertEqual(expected, manager._registry)

    def test_storehandlermanager__get_handler(self):
        """
        Verify StoreHandlerManager._get_handler returns handlers properly.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(StoreHandlerBase, {}, BogusModelType)
        handler = manager._get_handler(BogusModelType())
        self.assertIsInstance(handler, StoreHandlerBase)
