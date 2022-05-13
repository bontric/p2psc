"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
``[options.entry_points]`` section in ``setup.cfg``::

    console_scripts =
         fibonacci = p2psc.skeleton:run

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
import asyncio
import logging
import signal
import socket
import sys

from p2psc import __version__
from p2psc.common.args import parse_args
from p2psc.common.config import Config
from p2psc.common.logging import setup_logging
from p2psc.node import Node

__author__ = "Benedikt Wieder"
__copyright__ = "Benedikt Wieder"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

node = None
MAX_IP_GET_ATTEMPTS = 10


def get_ip():
    """ Hack to get the host's primary IP os-independently. 
    See here for more info: https://stackoverflow.com/a/28950776
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()
    return IP


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
    config = Config(args.config)

    if config["ip"] is None:
        for _ in range(MAX_IP_GET_ATTEMPTS):
            logging.info("Trying to find this hosts primary IP address.. ")
            config["ip"] = get_ip()
            if config["ip"] is not None:
                break
            logging.warning("Unable to get local IP address, retrying in 5 seconds..")
            await asyncio.sleep(5)

    if config["ip"] is None:
        logging.error("Unable to get local IP address")
        exit(1)

    logging.info(f"Using IP address: {config['ip']}")

    node = Node(config)

    _logger.info(f"Starting main loop for Node: {config['name']}")
    await node.serve()


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
