from asyncio import DatagramTransport, Transport
from dis import dis
import logging
from typing import Any, List, Tuple

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket
from contact.node import proto
from contact.node.peers.oscDispatcher import OscDispatcher

from contact.node.peers.peer import Peer
from contact.node.peers.peer import Peer, PeerType


class LocalClient(Peer):
    def __init__(self, transport: DatagramTransport, addr) -> None:
        super().__init__(addr, groups=None)
        self._type = PeerType.localClient
        self._transport = transport

    async def send(self, path: str, args: str):
        if self.is_expired() or self._transport is None:
            return

        self._transport.sendto(proto.osc_dgram(path, args) , self._addr)

    async def disconnect(self):
        pass # Do nothing since the server socket for clients should not be closed here 

    def is_expired(self):
        return False # local clients never expire
