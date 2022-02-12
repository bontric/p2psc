from __future__ import annotations
from typing import *

import zeroconf
import asyncio
import logging
import time

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from contact.node import proto
from contact.node.peers.localClient import LocalClient
from contact.node.peers.peer import Peer, PeerType
from contact.node.peers.localNode import LocalNode
from contact.node.zconf import NodeZconf


class NodeRegistry():

    def __init__(self, addr: Tuple[str, int], my_node: Peer, enable_zeroconf=False, node_callback: Callable[[str, int], None] = None, timeout=30) -> None:
        self._peers = {}  # type: Dict[str, Peer]
        self._timeout = timeout
        self._addr = addr
        self._running = False
        self._loop_task = None
        self._loop = asyncio.get_event_loop()

        # Transports for incoming connections
        self._ln_transport = None  # Local node transport
        self._ln_protocol = None
        self._lc_transport = None  # Local client transport
        self._lc_protocol = None

        # zeroconf
        self._enable_zeroconf = enable_zeroconf
        self._my_node = my_node  # type: Peer
        if enable_zeroconf:
            self._zconf = NodeZconf(addr, self._zconf_node_callback)

    def _zconf_node_callback(self, addr: Union[Tuple[str, int], None], state: zeroconf.ServiceStateChange):
        h = proto.hash(addr)

        if state == zeroconf.ServiceStateChange.Removed:
            logging.info(f"DISCONNECT node with addr: {addr}")
            if h in self._peers:
                del self._peers[h]
            else:
                logging.debug(f"Received Zconf REMOVED for unknown node: {addr}")
            return

        if state != zeroconf.ServiceStateChange.Added and state != zeroconf.ServiceStateChange.Updated:
            logging.warning("Received unknown zeroconf ServiceStateChange")
            return

        if h in self._peers:
            # Mark peers we already know as updated
            logging.debug(f"Updated node: {addr}")
            self._peers[h]._last_updateT = time.time()
            return

        logging.info(f"DISCOVERED node at {addr}, connecting..")

        peer = LocalNode(self._ln_transport, addr)
        self.add_peer(peer)

    def _osc_from_localClient(self, peer, bundle: OscBundle, message: OscMessage):
        if message is not None:
            # Message with no group is ONLY handled locally and forwarded to clients (if they subscribe)
            if not proto.path_has_group(message.address):
                # handle message locally
                asyncio.ensure_future(self._my_node.handle_message(peer, message))

                # forward message to clients except for sending
                for p in self.get_all(ptype=[PeerType.localClient, PeerType.remoteClient]):
                    if p == peer: 
                        continue
                    asyncio.ensure_future(p.handle_message(peer, message))
            else:
                # handle message locally
                asyncio.ensure_future(self._my_node.handle_message(peer, message))

                # forward message to clients and nodes except for sending
                for p in self.get_all():
                    if p == peer: 
                        continue
                    asyncio.ensure_future(p.handle_message(peer, message))
        else:
            logging.error("OSC Bundle messages are not supported yet!")
            # TODO: HANDLE BUNDLE
            # TODO: handle other messages from peer!

    def _osc_from_localNode(self, peer: Peer, bundle: OscBundle, message: OscMessage):
        if message is not None:
            # Handle ALL_NODES PEER_INFO here because only the registry needs to know
            if message.address == proto.ALL_NODES_PEER_INFO:
                self.__handle_peerinfo(peer, message)
                return

            if not proto.path_has_group(message.address):
                logging.warning(
                    f"Received invalid OSC from localNode {peer._addr}: (No group)")
                return

            logging.debug(
                f"Received OSC from LocalNode {peer._addr}: {message.address} {message.params}")

            # handle message locally
            asyncio.ensure_future(self._my_node.handle_message(peer, message))

            # forward message to clients
            for p in self.get_all(ptype=[PeerType.localClient, PeerType.remoteClient]):
                asyncio.ensure_future(p.handle_message(peer, message))
        else:
            logging.error("OSC Bundle messages are not supported yet!")
            # TODO: HANDLE BUNDLE
            # TODO: handle other messages from peer!

    def __handle_peerinfo(self, peer: Peer, message: OscMessage):
        if not Peer.is_valid_peerinfo(message.params):
            logging.warning(
                "Received invalid PEERINFO from {peer._addr}: {message.params}")
            return
        logging.debug(
            f"Received PEERINFO from {peer._addr}: {message.params}")

        peer.update_groups(message.params[3])
        peer.update_paths(message.params[4])
        peer._last_updateT = time.time()
        return

    class _PeerConnectionUdp():
        def __init__(self, registry: NodeRegistry, ptype: PeerType):
            self._registry = registry
            self._transport = None
            self._ptype = ptype
            self._peers = {str: Peer}

        def datagram_received(self, dgram, addr):
            """Called when a datagram is received from a newly connected peer."""

            # Parse OSC message
            try:
                if OscBundle.dgram_is_bundle(dgram):
                    bundle = OscBundle(dgram)
                    msg = None
                elif OscMessage.dgram_is_message(dgram):
                    msg = OscMessage(dgram)
                    bundle = None
                else:
                    raise  # Invalid message
            except:
                logging.warning(f"Received invalid OSC from {addr}")
                return

            peer = self._registry.get_peer(str(addr))

            # TODO: simplify this maybe?

            if self._ptype == PeerType.localClient:
                if peer is None:
                    peer = LocalClient(self._transport, addr)
                    self._registry.add_peer(peer)
                self._registry._osc_from_localClient(peer, bundle, msg)
                return

            elif self._ptype == PeerType.localNode:
                if peer is None:
                    peer = LocalNode(self._transport, addr)
                    self._registry.add_peer(peer)
                    logging.info(f"Client Connected from addr: {addr}")

                self._registry._osc_from_localNode(peer, bundle, msg)

        def connection_made(self, transport):
            self._transport = transport

        def connection_lost(self, exc):
            pass

        def error_received(self, exc):
            logging.error(
                f"The node connection for {self._ptype.name}s had an error: {str(exc)})")

    async def stop(self):
        if not self._running:
            return

        self._running = False
        self._loop_task.cancel()

        self._ln_transport.close()
        self._lc_transport.close()

        if self._enable_zeroconf:
            await self._zconf.stop()

    async def serve(self):
        if self._loop_task is not None:
            logging.warning("Node already running!")
            return

        self._ln_transport, self._ln_protocol = await self._loop.create_datagram_endpoint(lambda: self._PeerConnectionUdp(self, PeerType.localNode), local_addr=('0.0.0.0', self._addr[1]))
        self._lc_transport, self._lc_protocol = await self._loop.create_datagram_endpoint(lambda: self._PeerConnectionUdp(self, PeerType.localClient), local_addr=('0.0.0.0', self._addr[1]+1))

        if self._enable_zeroconf:
            await self._zconf.serve()

        self._loop_task = asyncio.create_task(self.__loop())
        await self._loop_task

    async def __loop(self):
        self._running = True
        while self._running:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                self._running = False
                break
            self.cleanup()

    def check_exists(self, peer: Peer):
        return peer._hash in self._peers

    def get_all(self, ptype=None) -> List[Peer]:
        if ptype is not None:
            if type(ptype) == list:
                return list(filter(lambda p: p._type in ptype, self._peers.values()))
            else:
                return list(filter(lambda p: p._type == ptype, self._peers.values()))

        return list(self._peers.values())

    def get_peer(self, addr: Tuple[str, int]) -> Peer:
        return self._peers.get(proto.hash(addr))

    def add_peer(self, peer: Peer):
        logging.info(
            f"Added {peer._type}: {peer._addr} {peer._groups} {list(peer._paths)}")
        self._peers[peer._hash] = peer

    def remove_peer(self, peer: Peer):
        if peer._hash in self._peers:
            del self._peers[peer._hash]

    def cleanup(self):
        for k in list(self._peers.keys()):
            if self._peers[k].is_expired():
                logging.info(f"Peer expired: {self._peers[k]._addr}")
                asyncio.ensure_future(self.disconnect_peer(self._peers[k]))

    async def disconnect_peer(self, peer: Peer):
        await peer.disconnect()
        del self._peers[peer._hash]
