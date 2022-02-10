# number of digits from sha256 we use


# zeroconf service type name
from argparse import ArgumentError
import hashlib
import pty
from typing import List, Tuple


ZC_SERVICE_TYPE = "_cnosc._udp.local."


# Groups
ALL_NODES = "ALL"

# Seperator for string lists
STR_LIST_SEP = " "

# Node commands
PEER_INFO = "/peerinfo"  # Request/Send Node Info
ALL_NODE_INFO = "/allnodeinfo"
TEST = "/test"  # print the message
REG_PATH = "/regpath"  # register a path
UNREG_PATH = "/unregpath"  # unregister a path
JOIN_GROUP = "/joingroup"  # join a group
LEAVE_GROUP = "/leavegroup"  # leave a group

# convenience functions for protocol
def path_has_group(path: str):
    return path.split('/')[1].upper() == path.split('/')[1]


def remove_group_from_path(path: str):
    return '/'+'/'.join(path.split('/')[2:])


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
