from audioop import add
from pydoc import cli
from tkinter import ALL
from unittest import mock
import pytest
from contact.node.peers.info import PeerInfo

__author__ = "Benedikt Wieder"
__copyright__ = "Benedikt Wieder"
__license__ = "MIT"

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_message import OscMessage

from contact.node.proto import STR_LIST_SEP

def test_serializeNodeInfo():
    ni1 = PeerInfo(addr=("127.0.0.1", 1234), groups=["a", "b"])
    
    # NOTE: It is important to use a list instead of a touple as 
    # osc argument.
    assert ni1.as_osc_args() == ["127.0.0.1", 1234, "a" + STR_LIST_SEP + "b"]

    mb = OscMessageBuilder("/test")
    for a in ni1.as_osc_args():    
        mb.add_arg(a)

    msg = OscMessage(mb.build().dgram)

    ni2 = PeerInfo()
    ni2.parse_osc_args(msg.params)

    assert ni1 == ni2
    assert ni1.groups == ni2.groups

def test_compareNodeInfo():

    ni1 = PeerInfo(addr=("127.0.0.1", 1234), groups=["a", "b"])
    ni2 = PeerInfo(addr=("127.0.0.1", 1234), groups=["c", "d"])
    ni3 = PeerInfo(addr=("192.168.0.5", 1234), groups=["f", "g"])
    
    assert ni1 == ni1 # same node 
    assert ni1 == ni2 # same ip/port, different groups
    assert ni1 != ni3 # different ip/port

def test_groupAddRemove():

    ni1 = PeerInfo(addr=("127.0.0.1", 1234), groups=["a", "b"])
    
    assert "test" not in ni1.groups
    ni1.add_group("test")
    assert "test" in ni1.groups
    ni1.remove_group("test")
    assert "test" not in ni1.groups
