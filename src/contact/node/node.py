from __future__ import annotations
import asyncio
import logging
from socket import timeout
from typing import Any, List, Tuple, Union

from contact.node.osc import NodeOsc
from contact.node.peers.localClient import LocalClient
from contact.node.peers.localNode import LocalNode
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType
from contact.node.registry import NodeRegistry
from contact.node import proto


class ContactNode(Peer, OscDispatcher):
    def __init__(self, name, addr, enable_zeroconf=True) -> None:
        self._local_client_addr = addr
        super().__init__(addr,groups=[name, proto.ALL_NODES])
        self._type = PeerType.localNode

        self._update_interval = 3
        self._registry = NodeRegistry(self._addr, self, enable_zeroconf, timeout=20)
        self._loop_task = None
        self._loop = asyncio.get_event_loop()

        self._ln_transport = None  # Local node transport
        self._ln_protocol = None
        self._lc_transport = None  # Local client transport
        self._lc_protocol = None

        self.add_path(proto.PEER_INFO, self._handle_peer_info)
        self.add_path(proto.TEST, self._handle_test)
        self.add_path(proto.ALL_NODE_INFO, self._handle_all_node_info)

    async def _handle_test(self, peer: Peer, path: str, *osc_args: List[Any]):
        print(f"Received TEST message from {peer._addr}: {path} {osc_args}")

    async def _handle_all_node_info(self, peer: Peer, path: str, *osc_args: List[Any]):
        if len(osc_args) != 0:
            return

        # TODO: this should be a bundle
        for p in self._registry.get_all(PeerType.localNode):
            asyncio.ensure_future(peer.send(proto.PEER_INFO, p.to_osc_args()))

        asyncio.ensure_future(peer.send(proto.PEER_INFO, self.to_osc_args()))

    async def _handle_peer_info(self, peer: Peer, path: str):
            # NodeInfo request with 0 args is a request for our own peerinfo
        logging.debug(f"Answering peerinfo request from {peer._addr}")
        await peer.send('/' + proto.ALL_NODES + proto.PEER_INFO, self.to_osc_args())
        

    def send_all(self, path, args, ptype=None):
        for p in self._registry.get_by_path(path):
            asyncio.ensure_future(p.send(path, args))

    def stop(self):
        if not self._running:
            return

        self._running = False
        self._loop_task.cancel()

    async def serve(self):
        if self._loop_task is not None:
            logging.warning("Node already running!")
            return

        self._loop_task = asyncio.create_task(self.__loop())
        await self._loop_task

    class _PeerFactory():
        def __init__(self, node: ContactNode, ptype: PeerType):
            self._cn = node
            self._transport = None
            self._ptype = ptype

        def datagram_received(self, data, addr):
            """Called when some datagram is received from a newly connected node."""
            peer = self._cn._registry._get_by_transport_addr(addr, self._ptype)

            if peer is None:
                if self._ptype == PeerType.localNode:
                    peer = LocalNode(self._cn._registry)
                elif self._ptype == PeerType.localClient:
                    peer = LocalClient(self._cn._registry)

                peer._transport_addr = addr
                peer._transport = self._transport
                logging.info(f"Client Connected from new transport {addr}")

            peer.datagram_received(data, addr)

        def connection_made(self, transport):
            self._transport = transport

        def connection_lost(self, exc):
            pass

        def error_received(self, exc):
            pass

    async def __loop(self):
        self._ln_transport, self._ln_protocol = await self._loop.create_datagram_endpoint(lambda: self._PeerFactory(self, PeerType.localNode), local_addr=self._addr)
        self._lc_transport, self._lc_protocol = await self._loop.create_datagram_endpoint(lambda: self._PeerFactory(self, PeerType.localClient), local_addr=(self._addr[0], self._addr[1]+1))
        self._registry_task = asyncio.create_task(self._registry.serve())

        self._running = True
        while self._running:
            try:
                await asyncio.sleep(self._update_interval)
            except asyncio.CancelledError:
                break
            # Update NodeInfo if necessary
            self.send_all('/' + proto.ALL_NODES + proto.PEER_INFO, self.to_osc_args())

        self._ln_transport.close()
        self._ln_transport.close()

        # terminate registry and wait till it is finished
        # NOTE: waiting untill proper zeoconfig shutdown
        self._registry.stop()
        await self._registry_task
