from audioop import add
from pydoc import cli
from tkinter import ALL
from unittest import mock
import pytest
from pytest_mock import MockerFixture

from contact.node.osc import NodeOsc
from contact.node.proto import ALL_NODES

__author__ = "Benedikt Wieder"
__copyright__ = "Benedikt Wieder"
__license__ = "MIT"

from pythonosc.osc_message_builder import OscMessageBuilder


def test_registerFunction(mocker: MockerFixture):
    nodeName = "TEST"

    n = NodeOsc(("127.0.0.1", 1234), [nodeName, ALL_NODES])

    client_addr = ("127.0.0.1", 1234)
    addr = "/test"
    args = [1, "test", 5.5]

    mockHandler = mocker.stub(name="osc_handler_stub")
    n.register_osc_path(addr, mockHandler, allow_remote= True)

    # Test with local address
    mb = OscMessageBuilder(addr)
    for a in args:
        mb.add_arg(a), args
    n._dispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_called_once_with(client_addr, addr, *args)

    # Test with ALL address
    mockHandler.reset_mock()  # reset mock number of function calls
    mb = OscMessageBuilder("/"+ALL_NODES+addr)
    for a in args:
        mb.add_arg(a), args
    n._groupDispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_called_once_with(client_addr, addr, *args)

    # Test with node's "group"
    mockHandler.reset_mock()  # reset mock number of function calls
    mb = OscMessageBuilder("/"+nodeName+addr)
    for a in args:
        mb.add_arg(a), args
    n._groupDispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_called_once_with(client_addr, addr, *args)

def test_localFunction(mocker: MockerFixture):
    nodeName = "TEST"

    n = NodeOsc(("127.0.0.1", 1234), [nodeName, ALL_NODES])

    client_addr = ("127.0.0.1", 1234)
    addr = "/test"
    args = [1, "test", 5.5]

    mockHandler = mocker.stub(name="osc_handler_stub")
    n.register_osc_path(addr, mockHandler)

    # Test with local address
    mb = OscMessageBuilder("/"+ALL_NODES + addr)
    for a in args:
        mb.add_arg(a), args

    n._groupDispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_not_called()

    mb.address = addr
    n._dispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_called_once_with(client_addr, addr, *args)
    
    mockHandler.reset_mock()
    n.unregister_osc_path(addr, mockHandler)
    n._dispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)
    mockHandler.assert_not_called()

def test_unregisteredFunction(mocker: MockerFixture):
    nodeName = "TEST"

    patched = mocker.patch.object(NodeOsc, "_handle_unmatched_local_function")
    n = NodeOsc(("127.0.0.1", 1234), [nodeName, ALL_NODES])

    client_addr = ("127.0.0.1", 1234)
    addr = "/test"
    args = [1, "test", 5.5]

    mb = OscMessageBuilder(addr)
    for a in args:
        mb.add_arg(a), args

    n._dispatcher.call_handlers_for_packet(mb.build().dgram, client_addr)

    patched.assert_called_once_with(client_addr, addr, *args)


def test_group_join_leave(mocker: MockerFixture):
    nodeName = "TEST"

    patched = mocker.patch.object(NodeOsc, "_handle_unmatched_group")
    n = NodeOsc(("127.0.0.1", 1234), [nodeName, ALL_NODES])

    client_addr = ("127.0.0.1", 1234)
    args = [1, 2, 3]
    group = "ABC"
    fun = "/test"
    addr = "/" + group + fun

    mockHandler = mocker.stub(name="osc_handler_stub")
    n.register_osc_path(fun, mockHandler, allow_remote=True)

    mb = OscMessageBuilder(addr)
    for a in args:
        mb.add_arg(a), args
    msg = mb.build().dgram

    # Test Group unjoined
    n._groupDispatcher.call_handlers_for_packet(msg, client_addr)

    patched.assert_called_once_with(client_addr, addr, *args)
    mockHandler.assert_not_called()

    # Reset mocks
    patched.reset_mock()
    mockHandler.reset_mock()

    # Test group after joining
    n.join_group(group)

    n._groupDispatcher.call_handlers_for_packet(msg, client_addr)

    patched.assert_not_called()
    mockHandler.assert_called_once_with(client_addr, fun, *args)

    # Reset mocks
    patched.reset_mock()
    mockHandler.reset_mock()

    # Test group after leaving
    n.leave_group(group)

    n._groupDispatcher.call_handlers_for_packet(msg, client_addr)

    patched.assert_called_once_with(client_addr, addr, *args)
    mockHandler.assert_not_called()
