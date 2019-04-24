from helper.argument_helper import get_arguments
from helper.config_helper import get_config

import logging
import os

logger = logging.getLogger()
token = None

def init(arguments):
    global logger

    global token

    init_arguments(arguments)

    logger.debug('token : %s', token)

def init_arguments(arguments):
    global logger

    global token

    arguments = get_arguments(arguments)

    if arguments.token:
        token = arguments.token
