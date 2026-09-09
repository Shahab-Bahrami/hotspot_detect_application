"""Dependency-free point-in-polygon reader for Natural Earth land GeoJSON."""
from __future__ import annotations
import json
from pathlib import Path

def _bbox(ring):
    xs=[p[0] for p in ring];ys=[p[1] for p in ring]
    return min(xs),min(ys),max(xs),max(ys)

def _on_segment(x,y,a,b,eps=1e-10):
    ax,ay=a;bx,by=b
    cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax)
    return abs(cross)<eps and min(ax,bx)-eps<=x<=max(ax,bx)+eps and min(ay,by)-eps<=y<=max(ay,by)+eps

def _inside_ring(x,y,ring):
    inside=False;j=len(ring)-1
    for i,(xi,yi) in enumerate(ring):
        xj,yj=ring[j]
        if _on_segment(x,y,(xi,yi),(xj,yj)):return True
        if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:inside=not inside
        j=i
    return inside

class LandMask:
    def __init__(self,path,lakes_path=None):
        self.polygons=self._read(path)
        self.lakes=self._read(lakes_path) if lakes_path else []

    @staticmethod
    def _read(path):
        raw=json.loads(Path(path).read_text(encoding='utf-8'));result=[]
        for feature in raw['features']:
            geom=feature['geometry'];coords=geom['coordinates']
            polygons=coords if geom['type']=='MultiPolygon' else [coords]
            for rings in polygons:
                if rings:result.append((_bbox(rings[0]),rings))
        return result

    @staticmethod
    def _contains(polygons,x,y):
        for (x0,y0,x1,y1),rings in polygons:
            if x0<=x<=x1 and y0<=y<=y1 and _inside_ring(x,y,rings[0]):
                return not any(_inside_ring(x,y,hole) for hole in rings[1:])
        return False

    def is_land(self,longitude,latitude):
        x=float(longitude);y=float(latitude)
        return self._contains(self.polygons,x,y) and not self._contains(self.lakes,x,y)
