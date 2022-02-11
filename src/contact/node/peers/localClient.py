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

from pythonosc.osc_message import OscMessage


class LocalClient(Peer):
    def __init__(self, transport: DatagramTransport, addr) -> None:
        super().__init__(addr, groups=None)
        self._type = PeerType.localClient
        self._transport = transport

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any], is_local=False):
        p = self.subscribed_path(path, is_local=is_local)

        if p is not None:
            await self._map[p](peer, path, osc_args)

    async def handle_message(self, peer: Peer, message: OscMessage, is_local=False):
        p = self.subscribed_path(message.address, is_local=is_local)

        if p is not None:
            await self._map[p](peer, message.address, message.params)

    async def disconnect(self):
        pass # Do nothing since the server socket for clients should not be closed here 

    def is_expired(self):
        return False # local clients never expire
