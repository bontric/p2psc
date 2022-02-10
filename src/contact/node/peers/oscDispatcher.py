
import abc
from typing import Any, List, Union
from contact.node.peers.peer import Peer


class OscDispatcher(abc.ABC):
    def on_osc(self, peer: Peer, path: str, args: Union[Any, List[Any]], exception: Exception = None):
        raise NotImplementedError()
