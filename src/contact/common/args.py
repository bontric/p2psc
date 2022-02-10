import logging
import argparse
import random
import string
from contact import __version__

def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="OSC Contact Node")
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        help="Set Node name",
        default=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)),
    )
    parser.add_argument(
        "-a",
        "--address",
        dest="addr",
        help="Set Node ip",
        default="127.0.0.1",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        dest="port",
        help="Set Node port",
        default="9139",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Contact {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)
