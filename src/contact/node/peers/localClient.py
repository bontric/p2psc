import logging
from socket import timeout
from typing import *
from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage
from contact.node import proto

from contact.node.peers.peer import Peer, PeerType


class LocalClient(Peer):
    """
    Represents a client which connects from the same machine or local network. 
    """

    def __init__(self, transport: DatagramTransport, addr) -> None:
        super().__init__(addr, groups=None, timeout=0)
        self._type = PeerType.localClient
        self._transport = transport

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any]):
        if self._transport.is_closing():
            return 

        # If path contains group, check if client explicitly subscribes this
        p = self.subscribed_path(path, is_local=True)

        # if not, remove group and try again
        if p is None:
            p = self.subscribed_path(proto.remove_group_from_path(path), is_local=True)

        if p is not None:
            logging.debug(f"Sending to localClient {self._addr}: {path} {osc_args}")
            self._transport.sendto(proto.osc_dgram(path, osc_args), self._addr)

    async def handle_message(self, peer: Peer, message: OscMessage):
        if self._transport.is_closing():
            return
        # If path contains group, check if client explicitly subscribes this
        p = self.subscribed_path(message.address, is_local=True)

        # if not, remove group and try again
        if p is None:
            p = self.subscribed_path(proto.remove_group_from_path(
                message.address), is_local=True)

        if p is not None:
            logging.debug(
                f"Sending to localNode {self._addr}: {message.address} {message.params}")
            self._transport.sendto(message.dgram, self._addr)
    
    async def send(self, path: str, osc_args: List[Any]):
        """ Send to peer without checking """
        if self._transport.is_closing():
            return
        logging.debug(f"Sending to localNode {self._addr}: {path} {osc_args}")
        self._transport.sendto(proto.osc_dgram(path, osc_args), self._addr)

    async def disconnect(self):
        pass  # Do nothing since the server socket for clients should not be closed here
