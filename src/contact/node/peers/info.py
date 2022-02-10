"""
The NodeInfo class contains all information related to a remote node.
"""


from __future__ import annotations
import time  # Import own class annotation
from typing import Any, List, Tuple
import hashlib

from attr import has

from contact.node.proto import STR_LIST_SEP


class PeerInfo:

    def __init__(self, addr: Tuple[str, int] = None, groups: List[str] = []):
        self.addr = addr
        self.groups = groups
        self.lastUpdateT = time.time()
        if addr is not None:
            self.hash = self._makeHash()

    def add_group(self, gName: str):
        self.groups.append(gName)

    def remove_group(self, gName: str):
        self.groups.remove(gName)

    def groups_as_string(self) -> str:
        return STR_LIST_SEP.join(self.groups)

    @staticmethod
    def string_to_groups(group_string:str) -> List[str]:
        return group_string.split(STR_LIST_SEP)

    def as_osc_args(self):
        return [self.addr[0], self.addr[1], self.groups_as_string()]

    def parse_osc_args(self, nIOsc: List[Any]):
        if len(nIOsc) != 3:
            raise ValueError("Invalid Node Info:", nIOsc)

        # TODO: There is absolutely no typechecking done here..
        # ALSO: FIXME: Calling the constructor here is weird
        self.__init__((nIOsc[0], nIOsc[1]), self.string_to_groups(nIOsc[2]))

    def __eq__(self, __o: PeerInfo) -> bool:
        # only allow one node for IP+port combinations
        # NOTE: This allows name-changes
        return self.hash == __o.hash

    def __str__(self):
        return str(self.addr) + str(self.groups)

    def _makeHash(self, portInc: int = 0):
        return PeerInfo.hash(self.addr)[:20] # first 20 bytes should be enough

    @staticmethod
    def hash(addr: Tuple(str, int)):
        h = hashlib.sha256()
        h.update(addr[0].encode())  # Node IP
        h.update(str(addr[1]).encode())  # Node Port (inc for compare)
        return h.digest().hex()

    #
    # 
    # def isInitiator(self, other: NodeInfo):
    #     if self.hash != other.hash:
    #         return self.hash > other.hash

    #     if self.addr[0] == other.addr[0] and self.addr[1] == other.addr[1]:
    #         logging.error("Node trying to connect to itself: ")
    #         raise ValueError("Node trying to connect to itself")

    #     # Handle absurdely unlikely collision.
    #     # If this happens more than once sha256 is broken..
    #     h1 = self.hash
    #     h2 = other.hash
    #     portInc = 1
    #     while h1 == h2:
    #         logging.warning("Hash collision Found, increasing port number:")
    #         h1 = self._makeHash(portInc)
    #         h2 = other._makeHash(portInc)
    #         portInc += 1

