from __future__ import annotations
import asyncio
import logging
from typing import List, Any

from contact.node.peers.localClient import LocalClient
from contact.node.peers.localNode import LocalNode
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType
from contact.node.registry import NodeRegistry
from contact.node import proto

from pythonosc.osc_message import OscMessage


class ContactNode(Peer, OscDispatcher):
    def __init__(self, name, addr, enable_zeroconf=True) -> None:
        self._local_client_addr = addr
        super().__init__(addr, groups=[name, proto.ALL_NODES])
        self._type = PeerType.localNode

        self._update_interval = 3  # TODO: Make configurable
        self._registry = NodeRegistry(self._addr, self, enable_zeroconf, timeout=20)
        self._loop_task = None
        self._loop = asyncio.get_event_loop()

        self.add_path(proto.PEER_INFO, self._handle_peer_info)
        self.add_path(proto.TEST, self._handle_test)
        self.add_path(proto.ALL_NODE_INFO, self._handle_all_node_info)

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any], is_local=False):
        p = self.subscribed_path(path, is_local=is_local)

        if p is not None:
            await self._map[p](peer, path, osc_args)

    async def handle_message(self, peer: Peer, message: OscMessage, is_local=False):
        p = self.subscribed_path(message.address, is_local=is_local)

        if p is not None:
            await self._map[p](peer, message.address, message.params)

    async def _handle_test(self, peer: Peer, path: str, *osc_args: List[Any]):
        print(f"Received TEST message from {peer._addr}: {path} {osc_args}")

    async def _handle_all_node_info(self, peer: Peer, path: str):
        # TODO: this should be a bundle
        for p in self._registry.get_all(PeerType.localNode):
            asyncio.ensure_future(peer.send(proto.PEER_INFO, p.to_osc_args()))

        asyncio.ensure_future(peer.send(proto.PEER_INFO, self.to_osc_args()))

    async def _handle_peer_info(self, peer: Peer, path: str, *osc_args: List[Any]):
        # NodeInfo request with 0 args is a request for our own peerinfo
        if len(osc_args) == 0:
            logging.debug(f"Answering peerinfo request from {peer._addr}")
            await peer.send('/' + proto.ALL_NODES + proto.PEER_INFO, self.to_osc_args())
            return

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
                asyncio.ensure_future(p.handle_message(self,
                                                       proto.osc_message(proto.PEER_INFO, self.to_osc_args()), is_local=True))
