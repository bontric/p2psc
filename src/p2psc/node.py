import asyncio
import logging
from typing import Tuple, Union

import zeroconf
from p2psc.common.config import Config
from p2psc.peerProtocol import OscHandler, OscProtocolUdp
from p2psc.peerInfo import PeerInfo, PeerType
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from p2psc.peerRegistry import PeerRegistry
from p2psc.zconf import NodeZconf
from p2psc import proto


class Node(OscHandler):
    def __init__(self, config: Config) -> None:
        self._registry = PeerRegistry(config["name"])
        self._addr = (config["ip"], config["port"])
        self._running = False
        self._transport = None  # type: OscProtocolUdp
        self._protocol = None  # type: OscProtocolUdp
        self._loop_task = None

        self._loop = asyncio.get_event_loop()

        self._enable_zeroconf = config["zeroconf"]
        if self._enable_zeroconf:
            self._zconf = NodeZconf(self._addr, self._zconf_node_callback)

    async def serve(self):
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
        Called by Zeroconf when a service changed state
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
            logging.debug(f"MDNS UPDATE node at {addr}")
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
            peer_type = self._registry.get_peer(addr).type #type: PeerInfo
        except LookupError:
            # If we don't know the peer we simply assume it is a client requesting us to forward the message
            # TODO: Any implications here?!
            peer_type = PeerType.client

        # Messages from clients are only forwarded to nodes
        if peer_type == PeerType.client:  
            for pi in self._registry.get_by_path(message.address): 
                logging.info(f"Forwarding {message.address} {message.params} to {pi.addr}")
                self._transport.sendto(message.dgram, pi.addr)
        else: # Messages from nodes are only forwarded to clients
            # remove group from path TODO: maybe preserve group?!
            m = proto.osc_dgram(proto.remove_group_from_path(message.address), message.params)
            for pi in self._registry.get_by_path(message.address): 
                self._transport.sendto(m, pi.addr)

    def _handle_local(self, addr, message: OscMessage):
        if message.address == proto.PEERINFO:
            if len(message.params) == 0:
                logging.debug(f"Peer {addr} requested info")
                self._transport.sendto(self._get_peerinfo_msg(), addr)
                return
            if not proto.is_valid_peerinfo(message.params):
                logging.warning(f"Received invalid peerinfo from {addr}: {message.params}")
                return
            self._registry.add_peer(PeerInfo.from_osc(addr, message.params))
        elif message.address == proto.ALL_PEERINFO:
            for pi in self._registry.get_by_type(PeerType.node):
                self._transport.sendto(proto.osc_dgram(proto.PEERINFO, pi.as_osc()), addr)
        elif message.address == proto.DISCONNECT:
            try:
                self._registry.remove_peer(addr)
            except LookupError:
                logging.warning(f"DISCONNECT request from unregistered peer: {addr}")