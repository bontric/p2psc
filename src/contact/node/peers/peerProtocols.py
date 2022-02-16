

import abc
import asyncio
import logging
from typing import Tuple
from Crypto.Cipher import AES

from contact.node.peers.peer import Peer, PeerType

from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle

UDP_MAX_DATA = 65507


class OscHandler():
    def on_osc(self, addr: Tuple[str, int], ptype: PeerType, msg: OscMessage = None, bundle: OscBundle = None):
        raise NotImplementedError()


class PeerProtocol(asyncio.DatagramProtocol):
    """ Mixed transport and protocol implementation

        Kinda Hacky but it works for now
    """

    def datagram_received(self, dgram, addr):
        raise NotImplementedError()

    def connection_made(self, transport):
        raise NotImplementedError()

    def connection_lost(self, exc):
        raise NotImplementedError()

    def error_received(self, exc):
        raise NotImplementedError()

    def sendto(self, data, addr):
        raise NotImplementedError()

    def close():
        raise NotImplementedError()

    def is_closing(self):
        raise NotImplementedError()


class OscProtocolUdp(PeerProtocol):
    def __init__(self, handler: OscHandler, ptype: PeerType):
        self._handler = handler
        self._transport = None  # type: asyncio.DatagramTransport
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

    def error_received(self, exc):
        logging.error(
            f"The node connection for {self._ptype.name}s had an error: {str(exc)})")

    def sendto(self, data, addr=None):
        self._transport.sendto(data, addr)

    def connection_lost(self, exc):
        pass
class OscProtocolUdpEncrypted(PeerProtocol):
    def __init__(self, handler: OscHandler, ptype: PeerType, key: bytes):
        self._handler = handler
        self._transport = None  # type: asyncio.DatagramTransport
        self._ptype = ptype
        self._key = key
        # recommended defaults used by Cipher.AES
        self._nonce_len = 16
        self._tag_len = 16

    def sendto(self, data: bytes, addr: Tuple[str, int]):
        cipher = AES.new(self._key, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(data)
        if len(nonce+ciphertext+tag) > UDP_MAX_DATA:
            logging.error("Unable to send encrypted packet: Packet too long")
            return
        self._transport.sendto(nonce+ciphertext+tag, addr)

    def is_closing(self):
        return self._transport.is_closing()

    def datagram_received(self, dgram, addr):
        """Called when a datagram is received from a newly connected peer."""

        if len(dgram) < self._nonce_len + self._tag_len:
            logging.info(f"Unable to decrypt packet from: {addr}")

        nonce = dgram[:self._nonce_len]
        tag = dgram[-self._tag_len:]

        cipher = AES.new(self._key, AES.MODE_EAX, nonce=nonce)
        data = cipher.decrypt(dgram[self._nonce_len:-self._tag_len])

        try:
            cipher.verify(tag)
        except ValueError:
            logging.info(
                f"Invalid packet from {addr}: Invalid Key or corrupted message")

        # Parse OSC message
        try:
            if OscBundle.dgram_is_bundle(data):
                bundle = OscBundle(data)
                msg = None
            elif OscMessage.dgram_is_message(data):
                msg = OscMessage(data)
                bundle = None
            else:
                raise  # Invalid message
        except:
            logging.warning(f"Received invalid OSC from {addr}")
            return

        self._handler.on_osc(addr, self._ptype, msg, bundle)

    def connection_made(self, transport: asyncio.DatagramTransport):
        self._transport = transport

    def connection_lost(self, exc):
        pass

    def error_received(self, exc):
        logging.error(
            f"The node connection for {self._ptype.name}s had an error: {str(exc)})")

    def close(self):
        self._transport.close()
