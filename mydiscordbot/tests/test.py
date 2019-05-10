import os.path, sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

import helper.argument_helper as argument_helper
import helper.config_helper as config_helper

import settings.settings as settings

import unittest
import numpy
import shutil

class ArgumentTest(unittest.TestCase):
    def test_short_option(self):
        arguments = argument_helper.get_arguments(['-v', '-t', 'my_token'])

        self.assertEqual(arguments.verbose, 1)
        self.assertEqual(arguments.token, 'my_token')

    def test_long_option(self):
        arguments = argument_helper.get_arguments(['--verbose', '--token', 'my_token'])

        self.assertEqual(arguments.verbose, 1)
        self.assertEqual(arguments.token, 'my_token')

    def test_multiple_verbose(self):
        verbosity_argument = '-'

        for verbosity_level in range(1, 10):
            verbosity_argument += 'v'
            arguments = argument_helper.get_arguments([verbosity_argument, '-t', 'my_token'])
            self.assertEqual(arguments.verbose, verbosity_level)

if __name__ == '__main__':
    iterations = 5

    for iteration in range(iterations):
        sucess = unittest.main(exit=False, argv=unitargs).result.wasSuccessful()

        if not sucess:
            sys.exit(1)
