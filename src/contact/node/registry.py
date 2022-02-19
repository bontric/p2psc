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
from contact.node.peers.peerProtocols import OscHandler, OscProtocolUdp, OscProtocolUdpEncrypted
from contact.node.peers.remoteNode import RemoteNode
from contact.node.zconf import NodeZconf

# Print received peerinfos -- only needed when debugging peerinfo stability
ENABLE_PEERINFO_LOGGING = False

class NodeRegistry(OscHandler):

    def __init__(self, my_node: Peer, addr_clients: Tuple[str, int], addr_local_nodes: Tuple[str, int],  addr_remote=None, key=None, enable_zeroconf=False, timeout=30) -> None:
        self._peers = {}  # type: Dict[str, Peer]
        self._timeout = timeout
        self._addr_clients = addr_clients
        self._addr_local_nodes = addr_local_nodes
        self._addr_remote = addr_remote
        self._running = False
        self._loop_task = None
        self._loop = asyncio.get_event_loop()
        self._key = key

        # Transports for incoming connections
        self._ln_transport = None  # Local node transport
        self._ln_protocol = None
        self._lc_transport = None  # Local client transport
        self._lc_protocol = None
        self._rn_transport = None  # Local client transport
        self._rn_protocol = None

        # zeroconf
        self._enable_zeroconf = enable_zeroconf
        self._my_node = my_node  # type: Peer
        if enable_zeroconf:
            self._zconf = NodeZconf(self._addr_local_nodes, self._zconf_node_callback)

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

        peer = LocalNode(self._ln_protocol, addr)
        self.add_peer(peer)

    def on_osc(self, addr: Tuple[str, int], ptype: PeerType, message: Union[OscBundle, OscMessage]):
        peer = self._peers.get(proto.hash(str(addr)))
        if peer is None:
            peer = self.init_peer(addr, ptype)

        if ptype == PeerType.localClient:
            self._osc_from_localClient(peer, message)
        elif ptype == PeerType.localNode:
            self._osc_from_localNode(peer, message)

    def _osc_from_localClient(self, peer:LocalClient, message: Union[OscBundle, OscMessage]):
        if type(message) == OscMessage:
            logging.debug(f"Received OSC from {peer._addr}: {message.address}, {message.params}")
            # Message with no group is ONLY handled locally and forwarded to clients (if they subscribe)
            if not proto.path_has_group(message.address):
                # forward message to clients except for sending
                for p in self.get_all(ptype=[PeerType.localClient]):
                    if p == peer:
                        continue
                    asyncio.ensure_future(p.handle_message(peer, message))
            else:
                # handle message locally
                asyncio.ensure_future(self._my_node.handle_message(peer, message))

                if proto.get_group_from_path(message.address) == proto.LOCAL_NODE:
                    return # no need to handle messsages elsewhere

                # forward message to clients and nodes except for sending
                for p in self.get_all():
                    if p == peer:
                        continue
                    asyncio.ensure_future(p.handle_message(peer, message))
        else:
            logging.error("OSC Bundle messages are not supported yet!")
            # TODO: HANDLE BUNDLE
            # TODO: handle other messages from peer!

    def _osc_from_localNode(self, peer: LocalNode, message: Union[OscBundle, OscMessage]):
        if type(message) == OscMessage:
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
            for p in self.get_all(ptype=[PeerType.localClient]):
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
        if ENABLE_PEERINFO_LOGGING:
            logging.debug(
                f"Received PEERINFO from {peer._addr}: {message.params}")

        peer.update_groups(message.params[3])
        peer.update_paths(message.params[4])
        peer._last_updateT = time.time()
        return

    async def stop(self):
        if not self._running:
            return

        self._running = False
        self._loop_task.cancel()

        self._ln_transport.close()
        self._lc_transport.close()
        if self._addr_remote is not None:
            self._rn_transport.close()

        if self._enable_zeroconf:
            await self._zconf.stop()

    async def serve(self):
        if self._loop_task is not None:
            logging.warning("Node already running!")
            return

        self._ln_transport, self._ln_protocol = await self._loop.create_datagram_endpoint(lambda: OscProtocolUdp(self, PeerType.localNode), local_addr=('0.0.0.0', self._addr_local_nodes[1]))
        self._lc_transport, self._lc_protocol = await self._loop.create_datagram_endpoint(lambda: OscProtocolUdp(self, PeerType.localClient), local_addr=('0.0.0.0', self._addr_clients[1]))
        logging.info(f"Listening for clients on: {self._addr_clients}")
        if self._addr_remote is not None:
            self._rn_transport, self._rn_protocol = await self._loop.create_datagram_endpoint(lambda: OscProtocolUdpEncrypted(self, PeerType.remoteNode, self._key), local_addr=self._addr_remote)

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

    async def connect_remote(self, addr, key):
        pass  # TODO
        # self._rn_transport, self._rn_protocol = await self._loop.create_datagram_endpoint(lambda: OscProtocolUdpEncrypted(self, PeerType.remoteNode, key), remote_addr=addr)
        #rN = RemoteNode(self._rn_protocol, addr)
        # self.add_peer(rN)

    def get_all(self, ptype=None) -> List[Peer]:
        if ptype is not None:
            if type(ptype) == list:
                return list(filter(lambda p: p._type in ptype, self._peers.values()))
            else:
                return list(filter(lambda p: p._type == ptype, self._peers.values()))

        return list(self._peers.values())

    def add_peer(self, peer: Peer):
        logging.info(
            f"Added {peer._type}: {peer._addr} {peer._groups} {list(peer._paths)}")
        self._peers[peer._hash] = peer

    def init_peer(self, addr, ptype):
        if ptype == PeerType.localClient:
            peer = LocalClient(self._lc_transport, addr)
        elif ptype == PeerType.localNode:
            peer = LocalNode(self._ln_protocol, addr)
        self.add_peer(peer)
        return peer

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
