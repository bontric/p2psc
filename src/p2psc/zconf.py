from typing import *
from argparse import ArgumentError
import asyncio
import logging
import socket
import ipaddress

from zeroconf import IPVersion, ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf, AsyncServiceBrowser

ZEROCONF_TTL = 1
ZEROCONF_UPDATE_INTERVAL = 15


class NodeZconf():
    ZC_SERVICE_TYPE = "_cnosc._udp.local."
    def __init__(self, addr: Tuple[str, int], node_callback: Callable[[Tuple[str, int], ServiceStateChange], None]) -> None:
        self._node_callback = node_callback
        self._addr = addr
        self._aiozc = None  # type: AsyncZeroconf
        self._running = False
        self._serve_task = None

        self._zcinfo = AsyncServiceInfo(
            NodeZconf.ZC_SERVICE_TYPE,
            f"{self.convert_addr_to_str(addr)}." + NodeZconf.ZC_SERVICE_TYPE,
            addresses=[addr[0]],
            port=addr[1]
        )

    @staticmethod
    def convert_addr_to_str(addr: Tuple[str, int]):
        ip = socket.inet_aton(addr[0]).hex()
        port = addr[1].to_bytes(2, 'little').hex()
        return ip+port

    @staticmethod
    def convert_str_to_addr(addr_str: str):
        if len(addr_str) != 12:
            raise ArgumentError(f"Unable to convert IP/port combination: {addr_str}")
        ip =  bytes.fromhex(addr_str[:8])
        port =  bytes.fromhex(addr_str[8:])
        return (socket.inet_ntoa(ip), int.from_bytes(port, 'little'))

    async def stop(self):
        if not self._running or self._serve_task is None:
            return
        self._running = False
        self._serve_task.cancel()
        await self._aiozc.async_unregister_service(self._zcinfo)
        logging.debug("Zeroconf shutdown finished")

    async def serve(self):
        self._aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)

        await self._aiozc.async_register_service(self._zcinfo, ttl=ZEROCONF_TTL)
        logging.debug("Finished zeroconf registration for node")

        self._aiozc_browser = AsyncServiceBrowser(
            self._aiozc.zeroconf, [NodeZconf.ZC_SERVICE_TYPE], handlers=[self._on_service_state_change])

        self._serve_task = asyncio.ensure_future(self.__loop())

    async def __loop(self):
        self._running = True
        while self._running:
            try:
                await asyncio.sleep(ZEROCONF_UPDATE_INTERVAL)
                asyncio.ensure_future(self._aiozc.async_update_service(self._zcinfo))
            except asyncio.CancelledError:
                return

    def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                                 ) -> None:
        # TODO: Do some more input validation
        name_split = name.split('.')

        if len(name_split) != 5:
            logging.warning(f"Received invalid Service name: {name}")
            return

        try:
            # TODO: IPv6 ..
            node_addr = self.convert_str_to_addr(name_split[0])
            if not ipaddress.IPv4Address(node_addr[0]).is_private:
                logging.warning(
                    f"Received non link-local IPv4 address from peer: {node_addr[0]}")
        except Exception as e:
            logging.warning(f"Received invalid Node address: {str(e)}")
            return

        if node_addr[0] == self._addr[0] and node_addr[1] == self._addr[1]:
            return  # ignore info from own node

        logging.debug(
            f"Service {name} of type {service_type} state changed: {state_change}")

        self._node_callback(node_addr, state_change)
