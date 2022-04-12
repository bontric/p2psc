from __future__ import annotations
import abc
import enum
import logging
import re
import time
from typing import *

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

from p2psc.node import proto


class PeerType(enum.Enum):
    localNode = 0
    localClient = 1
    remoteNode = 2


class Peer(abc.ABC):
    """
    Represents a generic peer in the network. These can be:
    + localNode:    Node on the same machine or local network
    + localClient:  Client on the same machine or local network
    + remoteNode:   Node connecting via the internet


    """
    def __init__(self, addr: Tuple[str, int], groups: List[str] = None, paths: List[str] = [],timeout=10) -> None:
        """ 
        Parameters:
            addr    : This peer's network addres which is used to uniquely identify it (IP + port)
            groups  : Groups to which this peer belongs (None for clients since they do not explicitly belong to groups)
            timeout : Time after which this node becomes "stale" if no PEERINFO request is received
                      (0 indicates this peer never times out (e.g.: TCP connection or clients)) 
        """
        self._addr = addr  # type: Tuple[str, int]
        self._hash = proto.hash(addr)  # type: str
        self._groups = groups  # type: List[str]
        self._type = None  # type: PeerType
        self._last_updateT = time.time()
        self._timeout = timeout  # type: int
        self._paths = paths # type: List[str]  

    async def send(self, peer: Peer, path: str, osc_args: List[Any]):
        """ Send the given message to the peer if it subscries the path """
        raise NotImplementedError()

    async def handle_message(self, peer: Peer, msg: Union[OscMessage, OscBundle, Tuple(str, List[Any])]):
        """ Send the given message to the peer if it subscries the path """
        raise NotImplementedError()

    async def disconnect(self):
        raise NotImplementedError()

    def __eq__(self, __o: Peer) -> bool:
        return self._hash == __o._hash

    def is_expired(self):
        return self._timeout > 0 and self._last_updateT < (time.time() - self._timeout)

    def to_osc_args(self):
        return proto.peerinfo_args(self._type.value, self._addr, self._groups, self._paths)

    @staticmethod
    def is_valid_peerinfo(args):
        return len(args) != 5 or type(args) != int or type(args[1]) != str \
            or type(args[2]) != int or type(args[3]) != str or type(args[4]) != str

    def update_paths(self, paths: str) -> Tuple[List[str], List[str]]:
        """ 
        Update paths from path list string and return newly added paths and removed paths as lists.
        Note: No handlers are added here since we only care about the paths

        Parameters:
            paths : Space-seperated list of osc paths
        Returns:
            updated_paths : (Newly added paths, Removed Paths)
        """
        old_paths = self._paths
        updated_paths = proto.str_to_list(paths)
        new = list(filter(lambda x: x not in old_paths, updated_paths))
        removed = list(filter(lambda x: x not in updated_paths, old_paths))

        for r in removed:
            self._paths.remove(r)
        for n in new:
            self._paths.append(n)

        if len(new) > 0 or len(removed) > 0:
            logging.info(f"{self._addr} updated paths: new: {new}, removed: {removed}")

        return (new, removed)

    def update_groups(self, groups: str) -> Tuple[List[str], List[str]]:
        """ 
        Update groups from group list string and return newly added groups and removed groups

        Parameters:
            groups (str): Space-seperated list of osc groups
        Returns:
            updated_groups ((List[str],(List[str]))): (Newly added groups, removed groups)
        """
        if self._groups is None:
            logging.error(
                "Update Groups, but this peer does not support groups: {groups}")
            return

        updated_groups = proto.str_to_list(groups)
        new = list(filter(lambda x: x not in self._groups, updated_groups))
        removed = list(filter(lambda x: x not in updated_groups, self._groups))

        self._groups = updated_groups

        if len(new) > 0 or len(removed) > 0:
            logging.info(f"{self._addr} updated groups: new: {new}, removed: {removed}")

        return (new, removed)

    def subscribed_path(self, path: str, is_local=False) -> bool:
        """
            Check if the given path matches any local path and return the local path if the given path had a group prefix
        Returns:
            Union[str, None]: local path (without group) if this peer has subscribed the given path, None otherwise
        """

        # if groups are present we check if the path matches our group
        if not is_local:
            if self._groups is None:
                return None
            if not proto.path_has_group(path):
                return None
            if proto.get_group_from_path(path) not in self._groups:
                return None
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

        for p in self._paths:
            if (patterncompiled.match(p)
                    or (('*' in p) and re.match(p.replace('*', '[^/]*?/*'), path))):
                return path
        return None
