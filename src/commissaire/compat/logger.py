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
Logging compat
"""

import logging as logging
from logging import config as _logging_config

from commissaire.compat import __python_version__, __python_semver__


if __python_version__ == '2' and int(__python_semver__[1]) < 7:

    def dictConfig(config):
        """
        Compatability function for Python < 2.7.

        :param config: The configuration dictionary
        :type config: dict

        .. warning::

           Does not support the all dictConfiguration options.
        """
        if int(config['version']) != 1:
            raise ValueError('Unsupported version: {0}'.format(
                config['version']))

        formatters = {}
        handlers = {}
        for name, kwargs in config['handlers'].items():
            mod, cls_name = kwargs['class'].rsplit('.', 1)
            del kwargs['class']  # class isn't an accepted kwarg

            # Formatter isn't an accepted kwarg
            formatter_name = kwargs.pop('formatter', None)
            # Stream isn't an accepted kwarg
            kwargs.pop('stream', None)

            level_name = kwargs.pop('level', 'NOTSET')

            # Get the handler class, create it with it's kwargs and set level
            cls = getattr(__import__(mod, fromlist=['True']), cls_name)
            handlers[name] = cls(**kwargs)
            handlers[name].setLevel(logging.getLevelName(level_name))
            # Add a formatter if one was provided
            if formatter_name:
                formatters[formatter_name] = logging.Formatter(
                    config['formatters'][formatter_name])
                handlers[name].setFormatter(formatters[formatter_name])

        # Merge the root logger into the loggers config
        config['loggers'][''] = config['root']
        # Configure the loggers
        for logger_name, logger_kwargs in config['loggers'].items():
            alogger = logging.getLogger(logger_name)
            for handler_name in logger_kwargs['handlers']:
                alogger.addHandler(handlers[handler_name])
            alogger.setLevel(logging.getLevelName(logger_kwargs['level']))
            alogger.propagate = logger_kwargs.get('propagate', True)

    _logging_config.dictConfig = dictConfig

logging.config = _logging_config
