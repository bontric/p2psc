from asyncio import Transport
from dis import dis
import logging
from typing import Any, List, Tuple

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket
from contact.node.peers.oscDispatcher import OscDispatcher

from contact.node.peers.peer import Peer
from contact.node.peers.peer import Peer, PeerType


class LocalClient(Peer):
    def __init__(self, dispatcher: OscDispatcher) -> None:
        super().__init__(groups=None)
        self._type = PeerType.localClient
        self._transport = None  # type: Transport
        self._dispatcher = dispatcher

    async def send(self, path: str, args: str):
        if self.is_expired() or self._transport is None:
            return

        mb = OscMessageBuilder(path)
        for a in args:
            mb.add_arg(a)

        if self._addr is None or not self.has_addr():
            logging.warning("Trying to send to uninitialized client {self.addr}")
        
        self._transport.sendto(mb.build().dgram, self._addr)

    async def disconnect(self):
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def disconnect(self):
        pass # Do nothing since the server socket for clients should not be closed here 

    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, dgram, addr):
        if not self.has_addr():
            self.set_addr(addr)
        for timed_message in OscPacket(dgram).messages:
            self._dispatcher.on_osc(
                self, timed_message.message.address, timed_message.message.params)

    def error_received(self, exc):
        self._dispatcher.on_osc(self, None, exception=exc)

    def connection_lost(self, exc):
        # this node will be cleaned up by the registry on the next cleanup
        self._last_updateT -= self._timeout
    
    def is_expired(self):
        return False # local clients never expire
