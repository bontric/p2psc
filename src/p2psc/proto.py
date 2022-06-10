from argparse import ArgumentError
import hashlib
from typing import *

from pythonosc.osc_message_builder import OscMessageBuilder

# Groups
ALL_NODES_GROUP = "ALL"

# Seperator for string lists
STR_LIST_SEP = " "

# Node commands
P2PSC_PREFIX = "p2psc"

# Request peerinfo
PEERINFO = '/'+P2PSC_PREFIX + "/peerinfo"

# request peerinfo for all nodes except local node
PEERINFOS = '/'+P2PSC_PREFIX + "/peerinfos"

# disconnect from node
DISCONNECT = '/'+P2PSC_PREFIX + "/disconnect"

# Get Nodenames in Network
PEERNAMES = '/'+P2PSC_PREFIX + "/peernames"
NODENAME = '/'+P2PSC_PREFIX + "/name"

# Get Groups
GROUPS = '/'+P2PSC_PREFIX + "/groups"

# Get paths for node (if no node is provided returns local paths)
GET_PATHS = '/'+P2PSC_PREFIX + "/paths"




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


def remove_group_from_path(path: str):
    return '/'+'/'.join(path.split('/')[2:])


def get_group_from_path(path: str):
    return path.split('/')[1]


def str_to_list(s: str):
    """ Convert a space seperated list string to list"""
    return list(filter(''.__ne__, s.split(STR_LIST_SEP)))


def list_to_str(groups: List[str]):
    """ Convert a list to a space seperated string"""
    return STR_LIST_SEP.join(groups)


def peerinfo_args(ptype: int, addr: Tuple[str, int], groups: List[str], paths: List[str]):
    """ Converts peer data into a list for osc_args. groups and paths are formatted as space-seperated lists (proto.STR_LIST_SEP) """
    if groups is None:
        raise ArgumentError(
            f"Trying to convert non-sharable Node to osc_args {addr}")
    return [ptype, STR_LIST_SEP.join(groups), STR_LIST_SEP.join(paths)]


def is_valid_peerinfo(args):
    return len(args) == 3 and type(args[0]) == int and type(args[1]) == str and type(args[2]) == str


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
