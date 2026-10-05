"""Inspect compiled world clip hulls; runtime probes remain the movement proof."""

import struct

from .geometry import dot
from .materials import finite_tuple

EMPTY, SOLID = -1,-2


class Hull:
    def __init__(self,bsp,hull=1,model=0):
        if hull not in (1,2) or not 0<=model<bsp.count("models"):
            raise ValueError("Choose an existing model and player/large clip hull")
        self.planes = list(struct.iter_unpack("<4fi",bsp.lump("planes")))
        self.nodes = list(struct.iter_unpack("<ihh" if bsp.format=="bsp29" else "<iii",bsp.lump("clipnodes")))
        self.root, = struct.unpack_from("<i",bsp.lump("models"),model*64+36+4*hull)

    def contents(self,point):
        point = finite_tuple(point,3,"Hull point")
        index,seen = self.root,set()
        while index>=0:
            if index>=len(self.nodes) or index in seen:
                raise ValueError("Invalid or cyclic clip hull")
            seen.add(index)
            plane,front,back = self.nodes[index]
            if not 0<=plane<len(self.planes):
                raise ValueError("Invalid clip plane")
            normal = self.planes[plane]
            index = front if dot(normal[:3],point)-normal[3]>=0 else back
        if not -6<=index<=-1:
            raise ValueError("Invalid clip contents")
        return index
