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
import base64
import logging
import os
import signal
import socket
import sys
from typing import Any, List, Tuple
import secrets

from contact import __version__
from contact.common.args import parse_args
from contact.common.config import ContactConfig
from contact.common.logging import setup_logging
from contact.node.node import ContactNode
from contact.node.peers.remoteNode import RemoteNode
from contact.node.zconf import NodeZconf

__author__ = "Benedikt Wieder"
__copyright__ = "Benedikt Wieder"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

node = None


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


def make_session(addr, key_generated=None, length=16):
    if key_generated is None:
        key_generated = secrets.token_urlsafe(nbytes=length)
    addr_str = NodeZconf.convert_addr_to_str(addr)
    session = addr_str+key_generated
    key = base64.urlsafe_b64encode(key_generated.encode('ascii'))
    return session, key


def parse_session(session: str):
    if len(session) < 12:
        logging.error(f"Session string is invalid: Invalid length {len(session)}")
        exit(-1)
    raddr = NodeZconf.convert_str_to_addr(session[:12])
    key = base64.urlsafe_b64encode(session[12:].encode('ascii'))
    return raddr, key


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
    config = ContactConfig(args.config)

    name = config["name"]
    if config["local_ip"] is None:
        logging.info("Trying to find this hosts primary IP address.. ")
        config["local_ip"] = get_ip()
        i = 0
        while config["local_ip"] is None:
            logging.warning("Unable to get local IP address, retrying in 10 seconds..")
            await asyncio.sleep(10)
            config["local_ip"] = get_ip()
            i += 1
            if i == 10:
                logging.error("Unable to get local IP address")
                return
        logging.info(f"Using IP address: {config['local_ip']}")

    if config["remote_host"]["enabled"]:
        # Setting a "session" in config is a hidden option for testing
        if config['remote_host'].get('session') is None:
            if config['remote_host'].get('ip') is None:
                logging.error("Remote IP must be set if remote_host is enabled")
                return
            gaddr = (config['remote_host']['ip'], config['remote_host']['port'])
            logging.info(f"Generating Session for connections on {gaddr}")
            session, key = make_session(gaddr)
            logging.info(f"Session String: {session}")
        else:
            logging.warning(
                f"UNSAFE: Reusing Session: {config['remote_host']['session']}")
            raddr, key = parse_session(config['remote_host']['session'])
            config['remote_host']['ip'] = raddr[0]
            config['remote_host']['port'] = raddr[1]
        config['remote_host']['key'] = key

    node = ContactNode(config)

    for s in config["remote_nodes"]["sessions"]:
        addr, key = parse_session(s)
        logging.info(f"Connecting to remote Node {addr} using key {key}")
        await node._registry.connect_remote(addr, key)

    if args.remotes is not None:
        for s in args.remotes.split(','):
            addr, key = parse_session(s)
            logging.info(f"Connecting to remote Node {addr} using key {key}")
            await node._registry.connect_remote(addr, key)

    _logger.info("Starting main loop")
    await node.serve()


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
