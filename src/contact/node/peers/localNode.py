from asyncio import Transport
import logging
import time
from typing import Any, List, Tuple, Union
from contact.node import proto
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType
from pythonosc.osc_packet import OscPacket
from pythonosc.osc_message_builder import OscMessageBuilder


class LocalNode(Peer):
    def __init__(self, dispatcher: OscDispatcher, addr: Tuple[int, str] = ("0.0.0.0", 0), groups: List[str] = [proto.ALL_NODES]) -> None:
        super().__init__(addr, groups=groups)

        self._dispatcher = dispatcher  # handles incoming OSC messages
        self._type = PeerType.localNode
        self._transport = None #type: Transport
        self._transport_addr = None
        self._is_client = self.has_addr()
        self.add_path(proto.PEER_INFO, self._handle_peer_info)

    async def _default_handler(self, peer: Peer, path: str, *args: Union[List[Any], None]):
        await self.send(path, args)

    async def _handle_peer_info(self, peer: Peer, path: str, ptype: PeerType, ip: str, port: int, groups:str, paths:str):
        if peer != self:
            return # Ignore peer info for other peers here 

        self.update_paths(paths)
        self.update_groups(groups)
        self._last_updateT = time.time()
        
    async def send(self, path: str, args: str):
        if self.is_expired() or self._transport.is_closing():
            self._dispatcher.on_osc(self, None, exception=ConnectionAbortedError())
            return

        mb = OscMessageBuilder(path)
        for a in args:
            mb.add_arg(a)
        
        if self._is_client:
            self._transport.sendto(mb.build().dgram)
        elif self._transport is not None and self._transport_addr is not None:
            self._transport.sendto(mb.build().dgram, self._transport_addr)
        else:
            logging.warning("Trying to send on uninitialized node {self.addr}")


    async def disconnect(self):
        # if node expires disconnect is called
        # which should only close a client socket
        # and never the server socket
        if self._is_client:
            self._transport.close()  
        

    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, dgram, addr):
        for t_msg in OscPacket(dgram).messages:
            if not self.has_addr():
                local_path = self.subscribed_path(t_msg.message.address) # remove group from path
                if local_path != proto.PEER_INFO:
                    logging.info("Received {timed_message.message.address} but still waiting for peerinfo..")
                    return
                self.set_addr((t_msg.message.params[1], t_msg.message.params[2]))
            self._dispatcher.on_osc(
                self, t_msg.message.address, t_msg.message.params)

    def error_received(self, exc):
        self._dispatcher.on_osc(self, None, exception=exc)

    def connection_lost(self, exc):
        # this node will be cleaned up by the registry on the next cleanup
        self._last_updateT -= self._timeout
