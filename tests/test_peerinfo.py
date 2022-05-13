import time
from p2psc import proto
from p2psc.peerInfo import PeerInfo, PeerType


def test_expires():
    pi = PeerInfo(("1.2.3.4", 1), type=PeerType.node)
    assert pi.is_expired() == False

    pi.last_update_t = time.time() - pi.NODE_EXPIRY_T
    assert pi.is_expired() == True

    pi.type = PeerType.client
    assert pi.is_expired() == False
    pi.type = PeerType.node

    pi.refresh()
    assert pi.is_expired() == False


def test_osc():
    groups = ["a"]
    paths = ["/a"]
    addr = ("1.2.3.4", 1)
    t = PeerType.node
    pi = PeerInfo(addr, groups=["a"], paths=["/a"], type=t)

    pi_osc = pi.as_osc()
    assert proto.is_valid_peerinfo(pi_osc)

    pi = PeerInfo.from_osc(addr, pi_osc)
    assert pi.addr == addr
    assert pi.groups == groups
    assert pi.type == t
    assert pi.paths == paths

def test_subscribes():
    pass # tested in registry_by_path