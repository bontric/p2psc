

import abc
import asyncio
import logging
from typing import Tuple, Union
from Crypto.Cipher import AES

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

UDP_MAX_DATA = 65507

class PeerProtocol(asyncio.DatagramProtocol):
    """ Mixed transport and protocol implementation

        Kinda Hacky but it works for now
    """

    def datagram_received(self, dgram, addr):
        raise NotImplementedError()

    def connection_made(self, transport):
        raise NotImplementedError()

    def connection_lost(self, exc):
        raise NotImplementedError()

    def error_received(self, exc):
        raise NotImplementedError()

    def sendto(self, data, addr):
        raise NotImplementedError()

    def close():
        raise NotImplementedError()

    def is_closing(self):
        raise NotImplementedError()

class OscHandler():
    async def on_osc(self, addr: Tuple[str, int], message: Union[OscBundle, OscMessage]):
        raise NotImplementedError()

class OscProtocolUdp(PeerProtocol):
    def __init__(self, handler: OscHandler):
        self._handler = handler
        self._transport = None  # type: asyncio.DatagramTransport

    def datagram_received(self, dgram, addr):
        """Called when a datagram is received from a newly connected peer."""

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

    def error_received(self, exc):
        logging.error(
            f"{str(exc)})")

    def sendto(self, data, addr):
        if self._transport is not None:
            self._transport.sendto(data, addr)
        else:
            raise ConnectionAbortedError()

    def connection_lost(self, exc):
        logging.info(f"Connection lost: {str(exc)})")
        self._transport = None

    def is_closing(self):
        return self._transport.is_closing()

