from argparse import ArgumentError
import hashlib
from typing import *

from pythonosc.osc_message_builder import OscMessageBuilder

# Zeroconf
ZC_SERVICE_TYPE = "_cnosc._udp.local."

# Groups
ALL_NODES = "ALL"
LOCAL_NODE = "N"

# Seperator for string lists
STR_LIST_SEP = " "

# Node commands
PEER_INFO = "/peerinfo"  # Request/Send Node Info
ALL_NODES_PEER_INFO  = "/" + ALL_NODES + "/" + PEER_INFO # peerinfo for all nodes
ALL_NODE_INFO = "/allnodeinfo"
TEST = "/test"  # print the message
JOIN_GROUP = "/joingroup"  # join a group
LEAVE_GROUP = "/leavegroup"  # leave a group
CLEAR_GROUPS = "/cleargroups" # clear all groups (except name and ALL)
ADD_PATH = "/addpath"  # register a path for this client
DEL_PATH = "/delpath"  # unregister a path for this client
CLEAR_PATHS = "/clearpaths" # remove all paths for this client
ADD_CLIENT = "/addclient" # add client (IP, Port, paths)
DEL_CLIENT = "/addclient" # delete client (IP, Port)
RESET = "/reset" # reset all groups and paths

# convenience functions for protocol


def osc_message(path, args):
    mb = OscMessageBuilder(path)
    for a in args:
        mb.add_arg(a)
    return mb.build()


def osc_dgram(path, args):
    mb = OscMessageBuilder(path)
    for a in args:
        mb.add_arg(a)
    return mb.build().dgram


def path_has_group(path: str):
    s = path.split('/')
    return len(s) > 2 and s[2] == ''


def remove_group_from_path(path: str):
    return '/'+'/'.join(path.split('/')[3:])


def get_group_from_path(path: str):
    return path.split('/')[1]


def str_to_list(l: str):
    """ Convert a space seperated list string to list"""
    return l.split(STR_LIST_SEP)


def peerinfo_args(ptype: int, addr: Tuple[str, int], groups: List[str], paths: List[str]):
    """ Converts peer data into a list for osc_args. groups and paths are formatted as space-seperated lists (proto.STR_LIST_SEP) """
    if groups is None:
        raise ArgumentError(
            f"Trying to convert non-sharable Node to osc_args {addr}")
    return [ptype, addr[0], addr[1], STR_LIST_SEP.join(groups), STR_LIST_SEP.join(paths)]


def hash(addr: Tuple[str, int]):
    """ Returns the sha256 of IP+port as hex string """
    h = hashlib.sha256()
    h.update(str(addr).encode())  # (IP,port)
    return h.digest().hex()


def is_initiator(own_addr: Tuple[str, int], other_addr: Tuple[str, int]):
    """ Compares the sha256 hash of two IP addressses converted to (little-endian) int. 
    The "larger" number initiates a connection """
    h_own = hashlib.sha256()
    h_own.update(str(own_addr).encode())  # (IP,port)
    h_other = hashlib.sha256()
    h_other.update(str(other_addr).encode())  # (IP,port)

    return int.from_bytes(h_own.digest(), "little") > int.from_bytes(h_other.digest(), "little")
