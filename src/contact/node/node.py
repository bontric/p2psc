from __future__ import annotations
from typing import *
import asyncio
import logging

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from contact.common.config import ContactConfig

from contact.node.peers.peer import Peer, PeerType
from contact.node.registry import NodeRegistry
from contact.node import proto

ENABLE_TEST = True


class ContactNode(Peer):
    def __init__(self, config: ContactConfig) -> None:
        client_addr = (config["local_ip"], config["clients"]["port"])
        local_nodes_addr = (config["local_ip"], config["local_nodes"]["port"])
        if config["remote_host"]["enabled"]:
            addr_remote = (config["remote_host"]["ip"], config["remote_host"]["port"])
            key = config["remote_host"]["key"]
        else:
            addr_remote = key = None
        super().__init__(local_nodes_addr, groups=[
            config["name"], proto.ALL_NODES], paths=[proto.TEST])
        self._type = PeerType.localNode

        self._update_interval = config["update_interval"]  # TODO: Make configurable
        self._registry = NodeRegistry(
            self, client_addr, local_nodes_addr, addr_remote, key, config["zeroconf"], config["timeout"])
        self._loop_task = None
        self._loop = asyncio.get_event_loop()
        self._client_paths = []

        self._map = {
            proto.PEER_INFO: self._handle_peer_info,
            proto.ALL_NODE_INFO:  self._handle_all_node_info,
            proto.JOIN_GROUP:  self._handle_join_group,
            proto.LEAVE_GROUP:  self._handle_leave_group,
            proto.CLEAR_GROUPS: self._handle_clear_groups,
            proto.ADD_PATH: self._handle_add_path,
            proto.DEL_PATH: self._handle_del_path,
            proto.CLEAR_PATHS: self._handle_clear_paths,
        }

        if ENABLE_TEST:
            self._map[proto.TEST] = self._handle_test

    def to_osc_args(self, ptype: PeerType):
        # merge all client paths
        if ptype == PeerType.localClient:
            paths = self._client_paths
            groups = self._groups[:2] + [proto.LOCAL_NODE] + self._groups[2:]
            return proto.peerinfo_args(self._type.value, self._addr, groups, paths)
        elif ptype == PeerType.localNode:
            return proto.peerinfo_args(self._type.value, self._addr, self._groups, self._client_paths)

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
                asyncio.ensure_future(p.send(proto.osc_message(
                    proto.ALL_NODES_PEER_INFO, self.to_osc_args(PeerType.localNode))))

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

    async def _handle_peer_info(self, peer: Peer, path: str, osc_args: List[Any]):
        # NodeInfo request with 0 args is a request for our own peerinfo
        if len(osc_args) != 0 or peer._type != PeerType.localClient:
            return

        logging.debug(f"Answering peerinfo request from {peer._addr}")
        await peer.send((proto.PEER_INFO, self.to_osc_args(PeerType.localClient)))

    async def _handle_all_node_info(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 0 or peer._type != PeerType.localClient:
            return

        # TODO: Use bundle?
        for p in self._registry.get_all(PeerType.localNode):
            asyncio.ensure_future(
                peer.send((proto.PEER_INFO, p.to_osc_args())))

        asyncio.ensure_future(
            peer.send((proto.PEER_INFO, self.to_osc_args(PeerType.localClient))))

    async def _handle_test(self, peer: Peer, path: str, osc_args: List[Any]):
        print(f"Received TEST message from {peer._addr}: {path} {osc_args}")

    async def _handle_join_group(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 1 or type(osc_args[0]) != str or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid joingroup from {peer._addr}")
            return
        logging.info(f"Received joingroup from {peer._addr}: {osc_args}")

        if osc_args[0] not in self._groups:
            self._groups.append(osc_args[0])
        else:
            logging.info(f"Already in group: {osc_args[0]}")

    async def _handle_leave_group(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 1 or type(osc_args[0]) != str or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid leavegroup from {peer._addr}")
            return
        logging.info(f"Received joingroup from {peer._addr}: {osc_args}")

        if osc_args[0] not in self._groups:
            logging.info(f"Not in group: {osc_args[0]}")
        else:
            self._groups.remove(osc_args[0])

    async def _handle_clear_groups(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 1 or type(osc_args[0]) != str or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid cleargroups from {peer._addr}")
            return
        logging.info(f"Received cleargroups from {peer._addr}: {osc_args}")

        # Remove all groups but name and ALL
        self._groups = self._groups[:2]

    async def _handle_add_path(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 1 or type(osc_args[0]) != str or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid addpath from {peer._addr}")
            return
        logging.info(f"Received addpath from {peer._addr}: {osc_args}")

        if osc_args[0] not in peer._paths:
            peer._paths.append(osc_args[0])

        # Update client paths: merge (sum((map(..)),[])) and remove duplicates (set())
        self._client_paths = list(set(
            sum(list(map(lambda x: x._paths, self._registry.get_all(PeerType.localClient))), [])))

    async def _handle_del_path(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 1 or type(osc_args[0]) != str or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid delpath from {peer._addr}")
            return
        logging.info(f"Received delpath from {peer._addr}: {osc_args}")

        if osc_args[0] in peer._paths:
            peer._paths.remove(osc_args[0])

        # Update client paths: merge (sum((map(..)),[])) and remove duplicates (set())
        self._client_paths = list(set(
            sum(list(map(lambda x: x._paths, self._registry.get_all(PeerType.localClient))), [])))

    async def _handle_clear_paths(self, peer: Peer, path: str, osc_args: List[Any]):
        if len(osc_args) != 0 or peer._type != PeerType.localClient:
            logging.warning(f"Received invalid clearpaths from {peer._addr}")
            return
        logging.info(f"Received clearpaths from {peer._addr}: {osc_args}")
        peer._paths = []
        # Update client paths: merge (sum((map(..)),[])) and remove duplicates (set())
        self._client_paths = list(set(
            sum(list(map(lambda x: x._paths, self._registry.get_all(PeerType.localClient))), [])))
