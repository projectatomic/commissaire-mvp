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
Test cases for the commissaire.oscmd module.
"""

from . import TestCase, available_os_types
from commissaire import oscmd


class _Test_OSCmd(TestCase):
    """
    Tests for the OSCmdBase class.
    """

    oscmdcls = None
    # (method_name, nargs)
    expected_methods = (('deploy', 1),
                        ('restart', 0),
                        ('upgrade', 0),
                        ('install_libselinux_python', 0),
                        ('install_docker', 0),
                        ('install_flannel', 0),
                        ('install_kube', 0))

    def before(self):
        """
        Sets up a fresh instance of the class before each run.
        """
        self.instance = self.oscmdcls()


class Test_OSCmdBase(_Test_OSCmd):
    """
    Tests for the OSCmdBase class.
    """

    oscmdcls = oscmd.OSCmdBase

    def test_oscmd_methods(self):
        """
        Verify OSCmdBase base methods all raises.
        """
        for meth, nargs in self.expected_methods:
            self.assertRaises(
                NotImplementedError,
                getattr(self.instance, meth),
                *tuple(range(nargs)))


class Test_get_oscmd(TestCase):

    def test_get_oscmd_with_valid_os_types(self):
        """
        Verify get_oscmd returns proper modules.
        """
        for os_type in available_os_types:
            self.assertEquals(
                'commissaire.oscmd.{0}'.format(os_type),
                oscmd.get_oscmd(os_type).__module__)

    def test_get_oscmd_with_invalid_os_types(self):
        """
        Verify get_oscmd errors when the os_type does not exist.
        """

        self.assertRaises(Exception, oscmd.get_oscmd, 'not_a_real_os_type')
