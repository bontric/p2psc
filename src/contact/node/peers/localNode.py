import logging
from typing import *
from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage

from contact.node import proto
from contact.node.peers.peer import Peer, PeerType


class LocalNode(Peer):
    """
    Represents a Node which connects from the same machine or local network. 
    """

    def __init__(self, transport: DatagramTransport, addr: Tuple[int, str], groups: List[str] = [proto.ALL_NODES]) -> None:
        super().__init__(addr, groups=groups, paths=[])

        self._type = PeerType.localNode
        self._transport = transport

        self.add_path(proto.PEER_INFO, None)

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any]):
        if self.is_expired() or self._transport.is_closing():
            return
        p = self.subscribed_path(path)

        if p is not None:
            logging.debug(f"Sending to localNode {self._addr}: {path} {osc_args}")
            self._transport.sendto(proto.osc_dgram(path, osc_args), self._addr)

    async def handle_message(self, peer: Peer, message: OscMessage):
        if self.is_expired() or self._transport.is_closing():
            return

        p = self.subscribed_path(message.address)

        if p is not None:
            logging.debug(
                f"Sending to localNode {self._addr}: {message.address} {message.params}")
            self._transport.sendto(message.dgram, self._addr)

    async def disconnect(self):
        pass  # Do nothing since the server socket for nodes should not be closed here
