import logging
from socket import timeout
from typing import *
from asyncio import DatagramTransport

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from p2psc.node import proto

from p2psc.node.peers.peer import Peer, PeerType


class LocalClient(Peer):
    """
    Represents a client which connects from the same machine or local network. 
    """

    def __init__(self, transport: DatagramTransport, addr) -> None:
        super().__init__(addr, groups=None, timeout=0)
        self._type = PeerType.localClient
        self._transport = transport

    async def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle, Tuple[str, List[Any]]]):
        if self._transport.is_closing():
            return

        if type(message) == Tuple:
            message = proto.osc_message(message[0], message[1])
        elif type(message) == OscBundle:
            raise NotImplementedError()

        # If path contains group, check if client explicitly subscribes this
        p = self.subscribed_path(message.address, is_local=True)
        if p is not None:
            logging.debug(
                f"Sending to localClient {self._addr}: {p} {message.params}")
            self._transport.sendto(message.dgram, self._addr)

        # if not, remove group and try again
        p = self.subscribed_path(proto.remove_group_from_path(
            message.address), is_local=True)

        if p is not None:
            # remove group from path when sending to client
            dgram = proto.osc_dgram(p, message.params)
            logging.debug(
                f"Sending to localClient {self._addr}: {p} {message.params}")
            self._transport.sendto(dgram, self._addr)

    async def send(self, message: Union[OscMessage, OscBundle, Tuple[str, List[Any]]]):
        if self._transport.is_closing():
            return

        if type(message) == tuple:
            message = proto.osc_message(message[0], message[1])
        elif type(message) == OscBundle:
            raise NotImplementedError()

        logging.debug(
            f"Sending to localClient {self._addr}: {message.address} {message.params}")
        self._transport.sendto(message.dgram, self._addr)

    async def disconnect(self):
        pass  # Do nothing since the server socket for clients should not be closed here
