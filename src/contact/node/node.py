from __future__ import annotations
from typing import *
import asyncio
import logging

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from contact.node.peers.peer import Peer, PeerType
from contact.node.registry import NodeRegistry
from contact.node import proto


class ContactNode(Peer):
    def __init__(self, name, addr, enable_zeroconf=True) -> None:
        self._local_client_addr = addr
        super().__init__(addr, groups=[name, proto.ALL_NODES], paths=[proto.TEST])
        self._type = PeerType.localNode

        self._update_interval = 3  # TODO: Make configurable
        self._registry = NodeRegistry(self._addr, self, enable_zeroconf, timeout=20)
        self._loop_task = None
        self._loop = asyncio.get_event_loop()

        self._map = {
            proto.PEER_INFO: self._handle_peer_info,
            proto.TEST: self._handle_test,
            proto.ALL_NODE_INFO:  self._handle_all_node_info,
            proto.JOIN_GROUP:  self._handle_join_group,
            proto.LEAVE_GROUP:  self._handle_leave_group,
            proto.ADD_PATH: self._handle_add_path,
            proto.DEL_PATH: self._handle_del_path,
        }

    async def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle, Tuple[str, List[Any]]]):
        if type(message) == tuple:
            message = proto.osc_message(message[0], message[1])
        elif type(message) == OscBundle:
            raise NotImplementedError()

        if proto.path_has_group(message.address):
            h = self._map.get(proto.remove_group_from_path(message.address))        
        else:
            h = self._map.get(message.address)
        
        if h is not None:
            await h(peer, message.address, message.params)

    async def _handle_test(self, peer: Peer, path: str, osc_args: List[Any]):
        print(f"Received TEST message from {peer._addr}: {path} {osc_args}")

    async def _handle_all_node_info(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 0 or peer._type != PeerType.localClient:
            return

        # TODO: Use bundle?
        for p in self._registry.get_all(PeerType.localNode):
            asyncio.ensure_future(peer.send((proto.PEER_INFO, p.to_osc_args())))

        asyncio.ensure_future(peer.send((proto.PEER_INFO, self.to_osc_args())))

    async def _handle_peer_info(self, peer: Peer, path: str, osc_args: List[Any]):
        # NodeInfo request with 0 args is a request for our own peerinfo
        if len(osc_args) != 0 or peer._type != PeerType.localClient:
            return

        logging.debug(f"Answering peerinfo request from {peer._addr}")
        await peer.send((proto.PEER_INFO, self.to_osc_args()))

    def stop(self):
        if not self._running:
            return

        self._running = False
        self._loop_task.cancel()

    async def serve(self):
        if self._loop_task is not None:
            logging.warning("Node already running!")
            return

        self._registry_task = asyncio.create_task(self._registry.serve())

        self._loop_task = asyncio.create_task(self.__loop())
        await self._loop_task

        # terminate registry and wait till it is finished
        # NOTE: waiting until proper zeroconf shutdown and UDP transport close
        await self._registry.stop()
        await self._registry_task

    async def __loop(self):
        self._running = True
        while self._running:
            try:
                await asyncio.sleep(self._update_interval)
            except asyncio.CancelledError:
                break

            for p in self._registry.get_all(ptype=PeerType.localNode):
                asyncio.ensure_future(p.send(proto.osc_message(proto.ALL_NODES_PEER_INFO, self.to_osc_args())))
