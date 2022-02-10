from __future__ import annotations

import abc
from argparse import ArgumentError
import enum
import logging
import re
import time
from typing import Any, Callable, Dict, List, Tuple, Union
from contact.node import proto


class PeerType(enum.Enum):
    localNode = 0
    localClient = 1
    remoteClient = 2
    remoteNode = 3


class Peer(abc.ABC):
    def __init__(self, addr: Tuple[str, int] = ("0.0.0.0", 0), groups: List[str] = None, timeout=30) -> None:
        self._addr = addr  # type: Tuple[str, int]
        self._hash = proto.hash(addr)  # type: str
        self._groups = groups  # type: List[str]
        self._type = None  # type: PeerType
        self._last_updateT = time.time()
        self._timeout = timeout  # type: int
        self._map = {} # type: Dict[str, Callable[[Peer, str, Union[List[Any], None]]]]

    async def send(self, path: str, args: Union[Any, List[Any]]):
        raise NotImplementedError()

    async def handle_path(self, peer: Peer, path: str, osc_args: List[Any]):
        p = self.subscribed_path(path)
        if p is not None:
            await self._map[p](peer, path, *osc_args)

    async def disconnect(self):
        raise NotImplementedError()

    async def _default_handler(peer: Peer, path: str, *args: Union[List[Any], None]):
        raise NotImplementedError()

    def __eq__(self, __o: Peer) -> bool:
        return self._hash == __o._hash

    def is_expired(self):
        return self._last_updateT < (time.time() - self._timeout)

    def has_addr(self):
        return self._addr[0] != "0.0.0.0"

    def set_addr(self, addr):
        self._addr = addr
        self._hash = proto.hash(addr)

    def to_osc_args(self):
        return proto.peerinfo_args(self._type.value, self._addr, self._groups, list(self._map.keys()))

    def add_path(self, path: str, handler: Callable[[Peer, str, Union[List[Any], None]], None]):
        self._map[path] = handler

    def update_paths(self, paths: str) -> Tuple[List[str], List[str]]:
        """ 
        Update paths from path list string and return newly added paths and removed paths as lists.
        New path are attached to this peer's default handler

        Parameters:
            paths (str): Space-seperated list of osc paths
        Returns:
            updated_paths ((List[str],(List[str]))): (Newly added paths, Removed Paths)
        """
        old_paths = list(self._map.keys())
        updated_paths = proto.str_to_list(paths)
        new = list(filter(lambda x: x not in old_paths, updated_paths))
        removed = list(filter(lambda x: x not in updated_paths, old_paths))

        for r in removed:
            del self._map[r]
        for n in new:
            self._map[n] = self._default_handler

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
            Union[str, None]: local path (without groop) if this peer has subscribed the given path, None otherwise
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

        for p in self._map.keys():
            if (patterncompiled.match(p)
                    or (('*' in p) and re.match(p.replace('*', '[^/]*?/*'), path))):
                return path
        return None
