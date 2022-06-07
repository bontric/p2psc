from enum import Enum
import re
import time
from typing import List

from p2psc import proto


class PeerType(Enum):
    node = 0
    client = 1


#   remoteNode = 2 # Unused for now

class PeerInfo:
    NODE_EXPIRY_T = 20  # in seconds

    def __init__(self, addr, groups: List[str] = [], paths: List[str] = [], type: PeerType = PeerType.client) -> None:
        self.addr = addr
        self.paths = paths
        self.groups = groups
        self.type = type
        self.last_update_t = time.time()

    @staticmethod
    def from_osc(addr, osc_args: List):
        """ 
        Returns a PeerInfo object derived from the given message and address. 
        Raises and exception if message is invalid TODO: Which?
        """
        # NOTE: Optional address in peerinfo?
        return PeerInfo(addr, type=PeerType(osc_args[0]), groups=proto.str_to_list(osc_args[1]), paths=proto.str_to_list(osc_args[2]))

    def as_osc(self):
        """
        Returns an OSC message which contains all information in this peerinfo
        """
        return proto.peerinfo_args(self.type.value, self.addr, self.groups, self.paths)
    
    def refresh(self):
        self.last_update_t = time.time()

    def is_expired(self):
        if self.type == PeerType.client:
            return False
        return time.time() >= self.last_update_t + PeerInfo.NODE_EXPIRY_T

    def subscribes(self, path:str):
        """
        Returns true if this peer subscribes the given path
        """

        # check if group is in path
        group = proto.get_group_from_path(path)
        if group != proto.ALL_NODES and group not in self.groups:
            return False

        path = proto.remove_group_from_path(path)
        # NOTE: Almost 1:1 copy from pythonosc, see: https://github.com/attwad/python-osc
        # First convert the address_pattern into a matchable regexp.
        # '?' in the OSC Address Pattern matches any single character.
        # Let's consider numbers and _ "characters" too here, it's not said
        # explicitly in the specification but it sounds good.
        escaped_address_pattern = re.escape(path)
        pattern = escaped_address_pattern.replace('\\?', '\\w?')
        # '*' in the OSC Address Pattern matches any sequence of zero or more
        # characters.
        pattern = pattern.replace('\\*', '[\w|\+]*')
        # The rest of the syntax in the specification is like the re module so
        # we're fine.
        pattern = pattern + '$'
        patterncompiled = re.compile(pattern)

        for p in self.paths:
            if (patterncompiled.match(p)
                    or (('*' in p) and re.match(p.replace('*', '[^/]*?/*'), path))):
                return True
        return False