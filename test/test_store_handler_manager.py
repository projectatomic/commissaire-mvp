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

from . import TestCase, TestModel

from commissaire.store import StoreHandlerBase
from commissaire.store.storehandlermanager import StoreHandlerManager


class PhonyStoreHandler(StoreHandlerBase):
    """
    Minimal store handler class for testing.
    """
    @classmethod
    def check_config(cls, config):
        """
        Base class requires this to be overridden.
        """
        pass


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
        manager._registry['test'] = TestModel
        clone_result = manager.clone()
        # The manager and the cloned_result should not be the same
        self.assertNotEqual(manager, clone_result)
        # But their content should be
        self.assertEqual(manager._registry, clone_result._registry)
        # And the handlers should still be empty
        self.assertEqual({}, manager._handlers)

    @mock.patch.object(PhonyStoreHandler, 'check_config')
    def test_storehandlermanager_get(self, PhonyStoreHandler):
        """
        Verify the StoreHandlerManager get method works as expected.
        """
        PhonyStoreHandler()._get.return_value = TestModel.new()
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        model_instance = TestModel.new()
        result = manager.get(model_instance)
        PhonyStoreHandler()._get.assert_called_once_with(model_instance)
        self.assertEqual(PhonyStoreHandler()._get.return_value, result)

    @mock.patch.object(PhonyStoreHandler, 'check_config')
    def test_storehandlermanager_delete(self, PhonyStoreHandler):
        """
        Verify the StoreHandlerManager delete method works as expected.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        model_instance = TestModel.new()
        manager.delete(model_instance)
        PhonyStoreHandler()._delete.assert_called_once_with(model_instance)

    @mock.patch.object(PhonyStoreHandler, 'check_config')
    def test_storehandlermanager_save(self, PhonyStoreHandler):
        """
        Verify the StoreHandlerManager save method works as expected.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        model_instance = TestModel.new()
        manager.save(model_instance)
        PhonyStoreHandler()._save.assert_called_once_with(model_instance)

    @mock.patch.object(PhonyStoreHandler, 'check_config')
    def test_storehandlermanager_list(self, PhonyStoreHandler):
        """
        Verify the StoreHandlerManager list method works as expected.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        model_instance = TestModel.new()
        manager.list(model_instance)
        PhonyStoreHandler()._list.assert_called_once_with(model_instance)

    def test_storehandlermanager_register_store_handler_with_one_model(self):
        """
        Verify StoreHandlerManager registers StoreHandlers properly with one model.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        expected = {
            TestModel: (PhonyStoreHandler, {}, (TestModel, )),
        }
        self.assertEqual(expected, manager._registry)

    def test_storehandlermanager_register_store_handler_with_multiple_models(self):
        """
        Verify StoreHandlerManager registers StoreHandlers properly with multiple models.
        """
        # Set up a few more bogus classes for testing
        class BogusStoreHandler(PhonyStoreHandler):
            pass

        class AnotherTestModel(TestModel):
            pass

        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        manager.register_store_handler(BogusStoreHandler, {}, AnotherTestModel)

        expected = {
            TestModel: (PhonyStoreHandler, {}, (TestModel, )),
            AnotherTestModel: (BogusStoreHandler, {}, (AnotherTestModel, )),
        }

        self.assertEqual(expected, manager._registry)

    def test_storehandlermanager__get_handler(self):
        """
        Verify StoreHandlerManager._get_handler returns handlers properly.
        """
        manager = StoreHandlerManager()
        manager.register_store_handler(PhonyStoreHandler, {}, TestModel)
        handler = manager._get_handler(TestModel.new())
        self.assertIsInstance(handler, PhonyStoreHandler)
