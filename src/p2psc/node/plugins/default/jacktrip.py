import abc
from typing import Dict, List, Union, Tuple, Any
from p2psc.node.node import Node
from p2psc.node.peers.peer import Peer

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from p2psc.node.plugins.plugin import P2PSCPlugin



class Jacktrip(P2PSCPlugin):
    def __init__(self) -> None:
        super().__init__()
    
    def getName() -> str:
        return "P2PSC JackTrip autoconnect"

    def getPaths() -> List[str]:
        return ["jacktrip/*"]

    def handle_message(self, peer: Peer, message: Union[OscMessage, OscBundle]):
        pass