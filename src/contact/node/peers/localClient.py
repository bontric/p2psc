import logging
from typing import *
from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage

from contact.node.peers.peer import Peer, PeerType


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
