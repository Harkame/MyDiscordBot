import argparse
import os

def get_arguments(arguments):
    argument_parser = argparse.ArgumentParser(description='My discord bot',
    formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=99999))

    argument_parser.add_argument(
        '-t', '--token',
        help = 'Discord API token' + os.linesep + 'Example : python japscandownloader/main.py -t mytoken',
        type = str,
        required=True,
    )

    argument_parser.add_argument(
        '-v', '--verbose',
        help = 'Active verbose mode, support different level' + os.linesep + 'Example : python mydiscordbot/main.py -vv',
        action = 'count',
    )

    return argument_parser.parse_args(arguments)
