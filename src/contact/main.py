"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
``[options.entry_points]`` section in ``setup.cfg``::

    console_scripts =
         fibonacci = contact.skeleton:run

Then run ``pip install .`` (or ``pip install -e .`` for editable mode)
which will install the command ``fibonacci`` inside your current environment.

Besides console scripts, the header (i.e. until ``_logger``...) of this file can
also be used as template for Python modules.

Note:
    This skeleton file can be safely removed if not needed!

References:
    - https://setuptools.readthedocs.io/en/latest/userguide/entry_point.html
    - https://pip.pypa.io/en/stable/reference/pip_install
"""
from ast import AsyncFunctionDef
import asyncio
import logging
import signal
import socket
import sys
from typing import Any, List, Tuple

from contact import __version__
from contact.common.args import parse_args
from contact.common.logging import setup_logging
from contact.node.node import ContactNode

__author__ = "Benedikt Wieder"
__copyright__ = "Benedikt Wieder"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

node = None

__RUNNING = True
def signal_handler(sig, frame):
    global node
    logging.info("CTRL+C pressed, shutting down..")
    if node is not None:
        logging.info("Stopping Node..")
        node.stop()

def main(args):
    args = parse_args(args)
    setup_logging(args.loglevel)
    signal.signal(signal.SIGINT, signal_handler)
    asyncio.get_event_loop().run_until_complete(main_loop(args))

async def main_loop(args):
    global node
    name = args.name.upper() # only allow upper case names
    if args.addr is not None:
        addr = (args.addr, args.port)
    else:
        addr = (socket.gethostbyname(socket.gethostname()), args.port)
    node = ContactNode(name, addr)

    _logger.info("Starting main loop")
    await node.serve()


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
