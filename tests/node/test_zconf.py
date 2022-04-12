import pytest 
from p2psc.node.zconf import NodeZconf


def test_conversion():
    addr = ("127.0.0.1", 1234)
    a = NodeZconf.convert_addr_to_str(addr)
    addr_conv = NodeZconf.convert_str_to_addr(a)

    assert addr[0] == addr_conv[0]
    assert addr[1] == addr_conv[1]