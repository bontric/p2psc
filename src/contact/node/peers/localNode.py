from asyncio import Transport
import logging
import time
from typing import Any, List, Tuple, Union
from contact.node import proto
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType

from asyncio import DatagramTransport


class LocalNode(Peer):
    def __init__(self, transport: DatagramTransport, addr: Tuple[int, str], groups: List[str] = [proto.ALL_NODES]) -> None:
        super().__init__(addr, groups=groups)

        self._type = PeerType.localNode
        self._transport = transport

        self.add_path(proto.PEER_INFO, None)

    
    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any]):
        if self.is_expired() or self._transport.is_closing():
            logging.warning(f"Trying to send on expired/disconnected peer {self._addr}")
        
        p = self.subscribed_path(path)
        
        if p is not None:
            logging.debug(f"Sending to localNode {self._addr}: {path} {osc_args}")
            self._transport.sendto(proto.osc_dgram(path, osc_args), self._addr)


    async def _default_handler(self, peer: Peer, path: str, *args: Union[List[Any], None]):
        # TODO: This handler is unnecessary overhead
        await self.send(path, args)

    async def send(self, path: str, args: str):
        pass


    async def disconnect(self):
        pass # Do nothing since the server socket for clients should not be closed here 
