import logging
from typing import Dict, List, Tuple
from p2psc import proto

from p2psc.peerInfo import PeerInfo, PeerType


class PeerRegistry:
    def __init__(self, name) -> None:
        self._node_name = name
        self.addr_peer_map = {}  # type: Dict[Tuple, PeerInfo]
        self._local_groups = [name]
        self._local_paths = []


    def get_local_paths(self) -> List[str]:
        """
        Return all paths subscribed by clients connected to this node
        """
        paths = []
        for pi in filter(lambda x: x.type == PeerType.client,  self.addr_peer_map.values()):
            paths.extend(pi.paths)
        return paths

    def get_local_groups(self) -> List[str]:
        """
        Return all groups subscribed by clients connected to this node
        """
        groups = []
        for pi in filter(lambda x: x.type == PeerType.client,  self.addr_peer_map.values()):
            groups.extend(pi.groups)
        groups = list(set(groups)) # remove duplicates
        groups.insert(0, self._node_name) # Insert own name as first element in groups
        return groups

    def _update_local(self):
        self._local_groups = self.get_local_groups()
        self._local_paths = self.get_local_paths()

    def get_by_type(self, t: PeerType) -> List[PeerInfo]:
        """
        Return all peerinfos with the given type
        """
        return list(filter(lambda x: x.type == t,  self.addr_peer_map.values()))

    def get_by_path(self, path: str, filter_type: PeerType = None) -> List[PeerInfo]:
        """
        Return all peerinfos subscribed to the given path
        """
        if filter_type is None:
            return list(filter(lambda x: x.subscribes(path, local_groups=self._local_groups),  self.addr_peer_map.values()))
        else:
            return list(filter(lambda x: x.type == filter_type and x.subscribes(path, local_groups=self._local_groups),  self.addr_peer_map.values()))

    def get_peer(self, addr) -> PeerInfo:
        """
        Returns a PeerInfo for the given address or raises LookupError 
        """
        if addr in self.addr_peer_map:
            return self.addr_peer_map[addr]
        else:
            raise LookupError()

    def remove_peer(self, addr):
        """
        Deletes the PeerInfo for the given address or raises LookupError 
        """
        if addr not in self.addr_peer_map:
            raise LookupError()
        
        logging.info(f"REMOVED: Peer {addr} from registry")
        del self.addr_peer_map[addr]
        self._update_local()
        

    def add_peer(self, pi: PeerInfo):
        """
        Add PeerInfo to registry
        """
        if pi.addr not in self.addr_peer_map:
            logging.info(f"ADDED: Peer {pi.addr} to registry")
        else:
            # This is rather spammy running multiple nodes
            # logging.debug(f"Peer {pi.addr} updated registry")
            pass
        self.addr_peer_map[pi.addr] = pi

        self._update_local()

    def cleanup(self):
        """
        Remove expired peerinfos from registry
        """
        for pi in list(self.addr_peer_map.values()):
            if pi.is_expired():
                logging.info(f"EXPIRED: Removing Peer {pi.addr} from registry")
                del self.addr_peer_map[pi.addr]
