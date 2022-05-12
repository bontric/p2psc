import abc
from typing import Dict, List, Union, Tuple, Any
from p2psc.node.node import Node
from p2psc.node.peers.peer import Peer

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from p2psc.node.plugins.plugin import P2PSCPlugin



class JacktripPlugin(P2PSCPlugin):
    def __init__(self, node: Node) -> None:
        super().__init__()

    def getName(self) -> str:
        return "P2PSC JackTrip autoconnect"

    def getPaths(self) -> List[str]:
        return ["jacktrip/*"]

    def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle]):
        print("Jacktrip  plugin received message: {}".format(message))
        pass