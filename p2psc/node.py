import asyncio
import logging
from typing import Tuple, Union

import zeroconf
from p2psc.common.config import Config
from p2psc.peerProtocol import OscHandler, OscProtocolUdp
from p2psc.peerInfo import PeerInfo, PeerType
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY

from p2psc.peerRegistry import PeerRegistry
from p2psc.zconf import NodeZconf
from p2psc import proto


class Node(OscHandler):
    def __init__(self, config: Config) -> None:
        self._registry = PeerRegistry(config["name"])
        self._addr = (config["ip"], config["port"])
        self._running = False
        self._transport = None  # type: asyncio.DatagramTransport
        self._protocol = None  # type: OscProtocolUdp
        self._loop_task = None
        self._config = config

        self._enable_zeroconf = config["zeroconf"]
        if self._enable_zeroconf:
            self._zconf = NodeZconf(self._addr, self._zconf_node_callback)

        self._osc_handlers = {
            proto.PEERINFO: self.__osc_peerinfo,        
            proto.PEERINFOS: self.__osc_peerinfo,        
            proto.DISCONNECT: self.__osc_disconnect,        
            proto.GET_PATHS: self.__osc_get_paths,        
            proto.NODENAME: self.__osc_nodename,        
            proto.PEERNAMES: self.__osc_peernames,        
            proto.GROUPS: self.__osc_groups,
        }

    async def serve(self):

        self._loop = asyncio.get_running_loop()

        if self._loop_task is not None:
            logging.warning("Registry already running!")
            return
        self._running = True

        self._transport, self._protocol = await self._loop.create_datagram_endpoint(lambda: OscProtocolUdp(self), local_addr=('0.0.0.0', self._addr[1]))

        if self._enable_zeroconf:
            await self._zconf.serve()

        self._loop_task = asyncio.create_task(self.__loop())
        await self._loop_task

    async def __loop(self):
        """
        Handles regular tasks
        """
        self._running = True
        while self._running:
            try:
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                self._running = False
                if self._enable_zeroconf:
                    await self._zconf.stop()
                break
            self._registry.cleanup()
            info = self._get_peerinfo_msg()

            # TODO: Only update peerinfos on change // implement ACK for peerinfo
            for pi in self._registry.get_by_type(PeerType.node):
                self._transport.sendto(info, pi.addr)

    def stop(self):
        """
        Stops the registry's async tasks
        """
        if not self._running:  # Already stopped
            return

        self._running = False
        self._loop_task.cancel()
        self._transport.close()

    def _get_peerinfo_msg(self):
        paths = self._registry.get_local_paths()
        groups = self._registry.get_local_groups()
        data = PeerInfo(self._addr, groups, paths, PeerType.node).as_osc()
        return proto.osc_dgram(proto.PEERINFO, data)

    def _zconf_node_callback(self, addr: Union[Tuple[str, int], None], state: zeroconf.ServiceStateChange):
        """
        Called by Zeroconf when a MDNS service changed state
        """
        if state == zeroconf.ServiceStateChange.Removed:
            try:
                logging.info(f"MDNS REMOVE node with addr: {addr}")
                self._registry.remove_peer(addr)
            except LookupError:
                logging.warning(f"MDNS REMOVED for unknown node: {addr}")
            return
        try:
            self._registry.get_peer(addr).refresh()
            # logging.debug(f"MDNS UPDATE node at {addr}")
        except LookupError:
            logging.info(f"MDNS DISCOVERED node at {addr}")
            pi = PeerInfo(addr, type=PeerType.node)
            self._registry.add_peer(pi)

    async def on_osc(self, addr: Tuple[str, int], message: Union[OscBundle, OscMessage]):
        """ 
        Handle incoming OSC messages
        """
        if type(message) == OscBundle:
            logging.error("OSC Bundle messages are not supported yet!")
            return

        # Peerinfo messages are handled locally
        if proto.get_group_from_path(message.address) == proto.P2PSC_PREFIX:
            self._handle_local(addr, message)
            return

        # All other messages are forwarded to clients/nodes depending on sender
        try:
            peer_type = self._registry.get_peer(addr).type  # type: PeerInfo
        except LookupError:
            # If we don't know the peer we simply assume it is a client requesting us to forward the message
            # TODO: Any implications here?!
            peer_type = PeerType.client

        # Messages from clients are only forwarded to nodes
        if peer_type == PeerType.client:
            for pi in self._registry.get_by_path(message.address, filter_type=PeerType.node):
                logging.info(
                    f"Forwarding {message.address} {message.params} to {pi.addr}")
                self._transport.sendto(message.dgram, pi.addr)
        else:  # Messages from nodes are only forwarded to clients
            # remove group from path
            m = proto.osc_dgram(proto.remove_group_from_path(
                message.address), message.params)
            for pi in self._registry.get_by_path(message.address, filter_type=PeerType.client):
                self._transport.sendto(m, pi.addr)

    def __osc_peerinfo(self, addr, message: OscMessage):
        if len(message.params) == 0:
            logging.debug(f"Peer {addr} requested info")
            self._transport.sendto(self._get_peerinfo_msg(), addr)
            return
        if not proto.is_valid_peerinfo(message.params):
            logging.warning(
                f"Received invalid peerinfo from {addr}: {message.params}")
            return
        self._registry.add_peer(PeerInfo.from_osc(addr, message.params))
    
    def __osc_peerinfos(self, addr, message: OscMessage):
        bb = OscBundleBuilder(IMMEDIATELY)
        for pi in self._registry.get_by_type(PeerType.node):
            bb.add_content(proto.osc_message(proto.PEERINFO, pi.as_osc()))
        self._transport.sendto(bb.build().dgram, addr)

    def __osc_disconnect(self,addr, message: OscMessage):
        try:
            self._registry.remove_peer(addr)
        except LookupError:
            logging.warning(f"DISCONNECT request from unregistered peer: {addr}")
    
    def __osc_get_paths(self,addr, message: OscMessage):
        if len(message.params) == 0:
            paths = proto.list_to_str(self._registry._local_paths)
            msg = proto.osc_dgram(proto.GET_PATHS, [self._registry._node_name, paths])
            self._transport.sendto(msg, addr)
            return
        if len(message.params) > 1 or type(message.params[0]) != str:
            logging.warning(
                f"Received Invalid Message from {addr}: {message.address}, {message.params}")
            return
        for pi in self._registry.get_by_type(PeerType.node):
            if len(pi.groups) < 1:
                continue
            if message.params[0] == pi.groups[0]:
                paths = proto.list_to_str(pi.paths)
                msg = proto.osc_dgram(proto.GET_PATHS, [pi.groups[0], paths])
                self._transport.sendto(msg, addr)

    def __osc_nodename(self, addr, message: OscMessage):
        if len(message.params) > 1:
            logging.warning(
                f"Received Invalid Message from {addr}: {message.address}, {message.params}")
        elif len(message.params) == 0:
            msg = proto.osc_dgram(proto.NODENAME, [self._registry._node_name])
            self._transport.sendto(msg, addr)
        else:
            if message.params[0] == "":
                self._registry.set_name(self._config["name"])
            else:
                self._registry.set_name(message.params[0])

    def __osc_peernames(self, addr, message: OscMessage):
        if len(message.params) != 0:
            logging.warning(
                f"Received Invalid Message from {addr}: {message.address}, {message.params}")
            return
        names = []
        for pi in self._registry.get_by_type(PeerType.node):
            if len(pi.groups) > 0:
                names.append(pi.groups[0])

        msg = proto.osc_dgram(proto.PEERNAMES, [proto.list_to_str(names)])
        self._transport.sendto(msg, addr)

    def __osc_groups(self, addr, message: OscMessage):
        if len(message.params) == 0:
            groups = self._registry._local_groups
            msg = proto.osc_dgram(proto.GROUPS, [proto.list_to_str(groups)])
            self._transport.sendto(msg, addr)
            return
        if len(message.params) > 1 or type(message.params[0]) != str:
            logging.warning(
                f"Received Invalid Message from {addr}: {message.address}, {message.params}")
            return

        for pi in self._registry.get_by_type(PeerType.node):
            if len(pi.groups) < 1:
                continue
            if message.params[0] == pi.groups[0]:
                msg = proto.osc_dgram(proto.GROUPS, [proto.list_to_str(pi.groups)])
                self._transport.sendto(msg, addr)

    def _handle_local(self, addr, message: OscMessage):
        """
        Handles OSC messages for local node
        """
        try:
            self._osc_handlers[message.address](addr, message)
        except KeyError:
            logging.info("Received Message with p2psc prefix but unknown path!")

            