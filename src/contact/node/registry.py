from argparse import ArgumentError
import asyncio
from audioop import add
import logging
import socket
import time
from typing import Any, Callable, List, Tuple, Dict, Union, cast

import zeroconf
from contact.node import proto
from contact.node.peers.oscDispatcher import OscDispatcher
from contact.node.peers.peer import Peer, PeerType
from contact.node.peers.localNode import LocalNode
from contact.node.zconf import NodeZconf


class NodeRegistry(OscDispatcher):

    def __init__(self, addr: Tuple[str, int], my_node: Peer, enable_zeroconf=False, node_callback: Callable[[str, int], None] = None, timeout=30) -> None:
        self._peers = {}  # type: Dict[str, Peer]
        self._timeout = timeout
        self._addr = addr
        self._running = False
        self._loop_task = None

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

        if not proto.is_initiator(self._addr, addr):
            logging.info(f"DISCOVERED node at {addr} (other is initiator)")
            return

        logging.info(f"DISCOVERED node at {addr}, connecting..")

        self.add_peer(LocalNode(self, addr))

        asyncio.ensure_future(asyncio.get_event_loop().create_datagram_endpoint(
            lambda: self._peers[h], remote_addr=addr))

    def on_osc(self, peer: Peer, path: str, osc_args: Union[Any, List[Any]] = None, exception: Exception = None):
        if exception is not None:
            logging.info(
                f"Peer {peer._addr} disconnected: {exception}")
            self.remove_peer(peer)
            return

        if peer._type == PeerType.localNode:
            # Received a message from a link-local node with GROUP prefix in path
            if not proto.path_has_group(path):
                logging.warning(
                    f"Received osc from {peer._addr} without group prefix : {path}")
                return

            if proto.get_group_from_path(path) not in self._my_node._groups:
                logging.warning(
                    f"Received osc from {peer._addr} for unmatched group: {path}")
                return

            logging.debug(f"Received osc from {peer._addr}: {path} {osc_args}")

            if peer._hash not in self._peers:
                self.add_peer(peer)

            # handle node info requests at the apropriate node:
            if peer.subscribed_path(path) == proto.PEER_INFO:
                asyncio.ensure_future(peer.handle_path(peer,path, osc_args))
                return
            
            # handle locally
            asyncio.ensure_future(self._my_node.handle_path(peer,path, osc_args))

        if peer._type == PeerType.localClient:
            if peer._hash not in self._peers:
                self.add_peer(peer)

            # handle locally
            asyncio.ensure_future(self._my_node.handle_path(peer,path, osc_args))


            if proto.path_has_group(path):
                # forward to all nodes if path contains group
                try: 
                    for p in self.get_all(ptype=PeerType.localNode):
                        asyncio.ensure_future(p.handle_path(peer, path, osc_args))
                except TypeError:
                # ignore type error because they indicate that the osc args differ from the handler signature
                # which is normal for e.g. peerinfo requests 
                    pass 




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

    async def __loop(self):
        if self._enable_zeroconf:
            self._zconf.serve()

        self._running = True

        while self._running:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                self._running = False
                break
            self.cleanup()

        if self._enable_zeroconf:
            await self._zconf.shutdown()

    def check_exists(self, peer: Peer):
        return peer._hash in self._peers

    def get_all(self, ptype=None) -> List[Peer]:
        if ptype is not None:
            return list(filter(lambda p: p._type == ptype, self._peers.values()))

        return list(self._peers.values())

    def _get_by_transport_addr(self, addr, ptype) -> Peer:
        for p in self._peers.values():
            if p._type == ptype and p._transport_addr is not None \
                    and p._transport_addr[0] == addr[0] and p._transport_addr[1] == addr[1]:
                return p
        return None

    def get_peer(self, addr: Tuple[str, int]) -> Peer:
        return self._peers.get(Peer.hash(addr))

    def get_by_path(self, path: str, ptype=None) -> List[Peer]:
        """ Return all peers matching the given group """
        peers = []

        for p in self._peers.values():
            if ptype is not None and p._type != ptype:
                continue  # filter out nodes not matching ptype
            if p.subscribed_path(path):
                peers.append(p)

        return peers

    def add_peer(self, peer: Peer):
        logging.info(f"Added {peer._type}: {peer._addr} {peer._groups} {list(peer._map.keys())}")
        self._peers[peer._hash] = peer

    def remove_peer(self, peer: Peer):
        if peer._hash in self._peers:
            del self._peers[peer._hash]

    def update_peer(self, peer: Peer, groups: str, paths: str) -> Tuple[Tuple[List[str], List[str]], Tuple[List[str], List[str]]]:
        if peer._hash in self._peers:
            up = self._peers[peer._hash].update_paths(paths)
            gu = self._peers[peer._hash].update_groups(groups)
            self._peers[peer._hash]._last_updateT = time.time()
        else:
            raise ArgumentError(
                f"Trying to update peer but it does not exist: {peer._addr}")
        return (up, gu)

    def cleanup(self):
        for k in list(self._peers.keys()):
            if self._peers[k].is_expired():
                logging.info(f"Peer expired: {self._peers[k]._addr}")
                asyncio.ensure_future(self.disconnect_peer(self._peers[k]))

    async def disconnect_peer(self, peer: Peer):
        await peer.disconnect()  # TODO: This might cause trouble with TCP connections
        del self._peers[peer._hash]
