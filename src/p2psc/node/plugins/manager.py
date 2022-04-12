import abc
from typing import Dict, List, Union, Tuple, Any
from p2psc.node.node import Node
from p2psc.node.peers.peer import Peer

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle


class PluginManager():
    def __init__(self, defaultPlugins: list[P2PSCPlugin]):
        self.defaultPlugins = defaultPlugins

    def loadPlugins(plugins: List[str]):
        pass
