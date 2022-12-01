

import abc
import asyncio
import logging
from typing import Tuple, Union

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

class OscHandler():
    async def on_osc(self, addr: Tuple[str, int], message: Union[OscBundle, OscMessage]):
        raise NotImplementedError()

class OscProtocolUdp(asyncio.DatagramProtocol):
    def __init__(self, handler: OscHandler):
        self._handler = handler
        self._transport = None  # type: asyncio.DatagramTransport

    def datagram_received(self, dgram, addr):
        """Called when a UDP message is received """

        # Parse OSC message
        try:
            if OscBundle.dgram_is_bundle(dgram):
                msg = OscBundle(dgram)
            elif OscMessage.dgram_is_message(dgram):
                msg = OscMessage(dgram)
            else:
                raise  # Invalid message
        except:
            logging.warning(f"Received invalid OSC from {addr}")
            return

        asyncio.ensure_future(self._handler.on_osc(addr, msg))

    def connection_made(self, transport):
        self._transport = transport

    def connection_lost(self, exc):
        logging.info(f"Connection lost: {str(exc)}")
        self._transport = None

