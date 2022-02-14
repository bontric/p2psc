

import logging
from typing import Tuple

from contact.node.peers.peer import PeerType


from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

class OscHandler():
    def on_osc(self, addr: Tuple[str,int], ptype: PeerType, msg: OscMessage = None, bundle: OscBundle = None):
        raise NotImplementedError()

class OscProtocolUdp():
    def __init__(self, handler: OscHandler, ptype: PeerType):
        self._handler = handler
        self._transport = None
        self._ptype = ptype

    def datagram_received(self, dgram, addr):
        """Called when a datagram is received from a newly connected peer."""

        # Parse OSC message
        try:
            if OscBundle.dgram_is_bundle(dgram):
                bundle = OscBundle(dgram)
                msg = None
            elif OscMessage.dgram_is_message(dgram):
                msg = OscMessage(dgram)
                bundle = None
            else:
                raise  # Invalid message
        except:
            logging.warning(f"Received invalid OSC from {addr}")
            return
        
        self._handler.on_osc(addr, self._ptype, msg, bundle)

    def connection_made(self, transport):
        self._transport = transport

    def connection_lost(self, exc):
        pass

    def error_received(self, exc):
        logging.error(
            f"The node connection for {self._ptype.name}s had an error: {str(exc)})")
