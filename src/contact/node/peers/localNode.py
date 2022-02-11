from asyncio import Transport
import logging
import time
from typing import Any, List, Tuple, Union
from contact.node import proto
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType

from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage


class LocalNode(Peer):
    def __init__(self, transport: DatagramTransport, addr: Tuple[int, str], groups: List[str] = [proto.ALL_NODES]) -> None:
        super().__init__(addr, groups=groups)

        self._type = PeerType.localNode
        self._transport = transport

        self.add_path(proto.PEER_INFO, None)

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any], is_local=False):
        if self.is_expired() or self._transport.is_closing():
            logging.warning(f"Trying to send on expired/disconnected peer {self._addr}")

        p = self.subscribed_path(path, is_local=is_local)

        if p is not None:
            logging.debug(f"Sending to localNode {self._addr}: {path} {osc_args}")
            self._transport.sendto(proto.osc_dgram(path, osc_args), self._addr)

    async def handle_message(self, peer: Peer, message: OscMessage, is_local=False):
        if self.is_expired() or self._transport.is_closing():
            logging.warning(f"Trying to send on expired/disconnected peer {self._addr}")

        p = self.subscribed_path(message.address, is_local=is_local)

        if p is not None:
            logging.debug(
                f"Sending to localNode {self._addr}: {message.address} {message.params}")
            self._transport.sendto(message.dgram, self._addr)

    async def disconnect(self):
        pass  # Do nothing since the server socket for nodes should not be closed here
