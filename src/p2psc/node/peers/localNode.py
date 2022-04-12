import logging
from typing import *
from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from p2psc.node import proto
from p2psc.node.peers.peer import Peer, PeerType


class LocalNode(Peer):
    """
    Represents a Node which connects from the same machine or local network. 
    """

    def __init__(self, transport: DatagramTransport, addr: Tuple[int, str], groups: List[str] = [proto.ALL_NODES]) -> None:
        super().__init__(addr, groups=groups, paths=[])

        self._type = PeerType.localNode
        self._transport = transport


    async def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle, Tuple[str, List[Any]]]):
        if self.is_expired() or self._transport.is_closing():
            return

        if type(message) == tuple:
            message = proto.osc_message(message[0], message[1])
        elif type(message) == OscBundle:
            raise NotImplementedError()

        p = self.subscribed_path(message.address)

        if p is not None:
            logging.debug(
                f"Sending to localNode {self._addr}: {message.address} {message.params}")
            self._transport.sendto(message.dgram, self._addr)
    
    async def send(self, message: Union[OscMessage, OscBundle, Tuple[str, List[Any]]]):
        if self._transport.is_closing():
            return

        if type(message) == Tuple:
            message = proto.osc_message(message[0], message[1])
        elif type(message) == OscBundle:
            raise NotImplementedError()

        logging.debug(
            f"Sending to localNode {self._addr}: {message.address} {message.params}")
        self._transport.sendto(message.dgram, self._addr)

    async def disconnect(self):
        pass  # Do nothing since the server socket for nodes should not be closed here
