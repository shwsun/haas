# Copyright 2013-2014 Massachusetts Open Cloud Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.  See the License for the specific language
# governing permissions and limitations under the License.

"""Load and query configuration data.

This module handles loading of the haas.cfg file, and querying the options
therein. the `cfg` attribute is an instance of `ConfigParser.RawConfigParser`.
Once `load` has been called, it will be ready to use.
"""

import logging
from logging import handlers
import importlib
import os
import sys


def configure_logging(log_level="INFO"):
    """Configure the logger according to the log_level argument
    """
    LOG_SET = ["CRITICAL", "DEBUG", "ERROR", "FATAL", "INFO", "WARN", "WARNING"]
    if log_level in LOG_SET:
        # Set to mnemonic log level
        logging.basicConfig(level=getattr(logging, log_level))
    else:
        # Set to 'warning', and warn that the config is bad
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger(__name__).warning(
                "Invalid debugging level %s defaulted to WARNING" % log_level)

    # Configure the formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging._defaultFormatter = formatter


def load_extensions():
    """Load extensions.

    Each extension is specified as ``module =`` in the ``[extensions]`` section
    of ``haas.cfg``. This must be called after ``load``.
    """
    extensions = ['haas.ext.auth.null']
    for name in extensions:
        importlib.import_module(name)
    for name in extensions:
        if hasattr(sys.modules[name], 'setup'):
            sys.modules[name].setup()


def setup():
    """Do full configuration setup.
    """
    configure_logging()
    load_extensions()
