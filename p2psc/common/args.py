import logging
import argparse
import random
import string
from p2psc import __version__

def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="OSC p2psc Node")
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Set configuration file path",
        default=None,
    )
    parser.add_argument(
        "-a",
        "--ip",
        dest="ip",
        help="Set ip address",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        help="Set network port",
        default=None,
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        help="Set node name",
        default=None,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="p2psc {ver}".format(ver=__version__),
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
