import pytest
from p2psc import proto
from p2psc.peerRegistry import PeerRegistry
from p2psc.peerInfo import PeerInfo, PeerType


def test_get_by_type():
    reg = PeerRegistry("name")
    pi_client = PeerInfo(("127.0.0.1", 1), type=PeerType.client)
    pi_node = PeerInfo(("127.0.0.1", 2), type=PeerType.node)
    reg.add_peer(pi_client)
    reg.add_peer(pi_node)

    pis = reg.get_by_type(PeerType.client)
    assert len(pis) == 1
    assert pis[0] == pi_client

    pis = reg.get_by_type(PeerType.node)
    assert len(pis) == 1
    assert pis[0] == pi_node


def test_get_local():
    reg = PeerRegistry("name")
    groups = ["A", "B", "name"]
    paths = ["a", "b"]
    not_groups = ["C"]
    not_paths = ["c"]
    pi_client = PeerInfo(
        ("127.0.0.1", 1), groups=[groups[0]], paths=[paths[0]], type=PeerType.client)
    pi_client2 = PeerInfo(
        ("127.0.0.1", 2), groups=[groups[1]], paths=[paths[1]], type=PeerType.client)
    pi_node = PeerInfo(
        ("127.0.0.1", 3), groups=[not_groups[0]], paths=[not_paths[0]], type=PeerType.node)
    reg.add_peer(pi_client)
    reg.add_peer(pi_client2)
    reg.add_peer(pi_node)

    # Check if groups match expected
    lgroups = reg.get_local_groups()
    for g in groups:
        assert g in lgroups

    # Check if paths match expected
    lpaths = reg.get_local_paths()
    for p in paths:
        assert p in lpaths
    
    reg = PeerRegistry("nodeD")
    lgroups = reg.get_local_groups()
    assert lgroups == ["nodeD"]


def test_cleanup():
    reg = PeerRegistry("name")
    pi_client = PeerInfo(("127.0.0.1", 1), type=PeerType.client)
    pi_node = PeerInfo(("127.0.0.1", 2), type=PeerType.node)
    reg.add_peer(pi_client)
    reg.add_peer(pi_node)

    # Check node is NOT removed if it is not expired
    assert pi_node.is_expired() == False
    reg.cleanup()
    assert reg.get_peer(pi_client.addr) == pi_client
    assert reg.get_peer(pi_node.addr) == pi_node

    # Check whether node is removed after expiry
    pi_node.last_update_t = 0
    assert pi_node.is_expired() == True
    reg.cleanup()
    assert reg.get_peer(pi_client.addr) == pi_client
    with pytest.raises(LookupError):
        reg.get_peer(pi_node.addr)


def test_by_path():
    reg = PeerRegistry("name")
    groups = ["name", "A", "B"]
    paths_c = ["/test", "/abc"]
    paths_n = ["/test", "/def"]
    c = PeerInfo(("127.0.0.1", 1), groups=groups[1:2], paths=paths_c, type=PeerType.client)
    n = PeerInfo(("127.0.0.1", 2), groups=groups[2:4], paths=paths_n, type=PeerType.node)
    reg.add_peer(c)
    reg.add_peer(n)

    peers = reg.get_by_path("/A/test")
    assert c in peers and n not in peers

    peers = reg.get_by_path("/B/test")
    assert c not in peers and n in peers

    peers = reg.get_by_path(f"/{proto.ALL_NODES}/test")
    assert c in peers and n in peers

    peers = reg.get_by_path("/name/test")
    assert c in peers and n not in peers

    peers = reg.get_by_path(f"/{proto.ALL_NODES}/abc")
    assert c in peers and n not in peers

    peers = reg.get_by_path(f"/{proto.ALL_NODES}/def")
    assert c not in peers and n in peers

    peers = reg.get_by_path(f"/{proto.ALL_NODES}/xyz")
    assert c not in peers and n not in peers

def test_add():
    reg = PeerRegistry("name")
    groups = ["A", "B"]
    paths_c = ["/test", "/abc"]
    c = PeerInfo(("127.0.0.1", 1), groups=groups, paths=paths_c, type=PeerType.client)
    reg.add_peer(c)

    assert "name" in c.groups
    assert proto.ALL_NODES not in c.groups
