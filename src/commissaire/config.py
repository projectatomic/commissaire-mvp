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
Configuration.
"""

import etcd
import logging


class Config(dict):
    """
    Configuration container.
    """

    def __init__(self, listen={}, etcd={}, kubernetes={}):
        """
        Creates an instance of the Config class.

        :param listen: Structure containing the server listening data.
        :type listen: dict
        :param etcd: Structure containing the etcd connection data.
        :type etcd: dict
        :param kubernetes: Structure containing the kubernetes connection data.
        :type kubernets: dict
        :returns: commissaire.config.Config
        """
        self.listen = listen
        self.etcd = etcd
        self.kubernetes = kubernetes
