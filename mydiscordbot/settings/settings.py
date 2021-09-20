from helpers import helper_config, helper_argument

import os

import logging

logger = logging.getLogger()
token = None


def init(arguments):
    global token

    global playists

    playists = helper_config.get_config(os.path.join(".", "playists.yml"))

    if playists is None:
        playists = []

    print(playists)

    init_arguments(arguments)

    logger.debug("token : %s", token)


def init_arguments(arguments):
    global logger

    global token

    arguments = helper_argument.get_arguments(arguments)

    if arguments.verbose:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s :: %(levelname)s :: %(module)s :: %(lineno)s :: %(funcName)s :: %(message)s"
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        if arguments.verbose == 0:
            logger.setLevel(logging.NOTSET)
        elif arguments.verbose == 1:
            logger.setLevel(logging.DEBUG)
        elif arguments.verbose == 2:
            logger.setLevel(logging.INFO)
        elif arguments.verbose == 3:
            logger.setLevel(logging.WARNING)
        elif arguments.verbose == 4:
            logger.setLevel(logging.ERROR)
        elif arguments.verbose == 5:
            logger.setLevel(logging.CRITICAL)

        logger.addHandler(stream_handler)

    if arguments.token:
        token = arguments.token
