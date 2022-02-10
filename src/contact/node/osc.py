from calendar import c
import logging
import asyncio
import socket
from typing import Any, List, Tuple, Callable, Dict, Union

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from contact.node.peers.peer import PeerType

from contact.node.proto import ALL_NODES


class NodeOsc:
    def __init__(self, addr: Tuple[str, int], handler, ptype: PeerType) -> None:
        self._addr = addr

        # handles messages from local connection
        self._dispatcher = Dispatcher()
        self._dispatcher.map("*", handler, ptype, needs_reply_address= True)

        # Async UDP server
        self._server = AsyncIOOSCUDPServer(
            addr, self._dispatcher, asyncio.get_event_loop())
        self._transport = None
        self._protocol = None

    async def serve(self):
        logging.info("Serving OSC server on: {}".format(self._addr))
        self._transport, self._protocol = await self._server.create_serve_endpoint()

    def stop(self):
        logging.info("Closing OSC server on: {}".format(self._addr))
        self._transport.close()