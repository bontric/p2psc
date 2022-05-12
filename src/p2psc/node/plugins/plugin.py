import abc
from typing import Dict, List, Union, Tuple, Any
from p2psc.node.node import Node
from p2psc.node.peers.peer import Peer

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle


class P2PSCPlugin(abc.ABC):
    def __init__(self, node: Node):
        raise NotImplementedError()

    def getName(self) -> str:
        """ Returns the Name of this Plugin """
        raise NotImplementedError()

    def getPaths(self) -> List[str]:
        """ Return Paths which this plugin subscribes """
        raise NotImplementedError()

    async def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle]):
        """ Handle an incoming message matching one of the paths returned by getPaths() """
        raise NotImplementedError()

    async def handle_peer_update(self, peerInfos: List[Any]):
        raise NotImplementedError()

    def shutdown(self):
        raise NotImplementedError()



