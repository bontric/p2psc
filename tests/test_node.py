
import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock
from pytest_mock import MockerFixture
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from p2psc import proto
from p2psc.common.config import Config

from p2psc.node import Node
from p2psc.peerInfo import PeerInfo, PeerType

def make_config(name='test'):
    return {
        "name": name,
        "zeroconf": True,
        "timeout": 20,
        "update_interval": 3,
        "ip": "127.0.0.1",
        "port": 3760,
    }

class FakeTransport(asyncio.DatagramTransport):
    pass


class Test(IsolatedAsyncioTestCase):
    async def test_on_osc(self):

        node = Node(make_config())
        node._handle_local = MagicMock()
        node._transport = FakeTransport()
        node._transport.sendto = MagicMock()
        addr = ("127.0.0.1", 1)

        # Local functions are handled
        for path in [proto.PEERINFO, proto.ALL_PEERINFO, proto.DISCONNECT]:
            msg = OscMessageBuilder(path).build()
            await node.on_osc(addr, msg)
            node._handle_local.assert_called_once_with(addr, msg)
            node._transport.sendto.assert_not_called() # Make sure nothing else happend
            node._handle_local.reset_mock()

        # osc received by client (default) must be forwarded to all NODES
        node._registry.get_by_path = MagicMock(return_value=[PeerInfo(addr, type=PeerType.node)])            
        msg = OscMessageBuilder("/test").build()
        await node.on_osc(addr, msg)
        node._registry.get_by_path.assert_called_once_with(msg.address, filter_type=PeerType.node)
        node._transport.sendto.assert_called_once_with(msg.dgram, addr)
        node._handle_local.assert_not_called() # make sure nothing else happend

        # Reset    
        node._registry.get_by_path.reset_mock()
        node._transport.sendto.reset_mock()

        # osc received by node must be forwarded to all clients
        node._registry.get_peer = MagicMock(return_value=PeerInfo(addr, type=PeerType.node))
        node._registry.get_by_path = MagicMock(return_value=[PeerInfo(addr)])            
        msg = OscMessageBuilder("/ALL/test").build()
        await node.on_osc(addr, msg)
        node._registry.get_peer.assert_called_once_with(addr)
        node._registry.get_by_path.assert_called_once_with(msg.address, filter_type=PeerType.client)
        msg = OscMessageBuilder(proto.remove_group_from_path(msg.address)).build()
        node._transport.sendto.assert_called_once_with(msg.dgram, addr)
        node._handle_local.assert_not_called() # make sure nothing else happend
