import abc
import logging
from typing import List, Tuple
from p2psc.node.node import Node
from p2psc.node.plugins.default.jacktrip import JacktripPlugin

from p2psc.node.plugins.plugin import P2PSCPlugin

class PluginManager():
    __default_plugins = {"jacktrip": JacktripPlugin}

    def __init__(self, node: Node, defaultPlugins: list[str]):
        self.default_plugins = [] # type: List[P2PSCPlugin]
        self.plugins = []
        self.node = node
        for p in self.default_plugins:
            try: 
              # map an instantiate plugins 
              self.default_plugins.append(PluginManager.__default_plugins[p](node))
            except KeyError:
                logging.warning("Trying to load nonexistent default plugin: {}".format(p))


    def loadPlugins(plugins: List[Tuple[str, str]]):
        #for p in plugins:
        #    class_name = p[0]
        #    file_name = p[1]
        raise NotImplementedError()