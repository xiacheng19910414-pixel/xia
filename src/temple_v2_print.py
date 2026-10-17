"""Manufacturing adaptation of the approved V2 brush-calligraphy drawing.

Small roundings are applied to the *source polygons*, never by deleting mesh
faces. The review drawing is preserved separately for comparison.
"""
from shapely import Polygon, union_all, set_precision
from src.temple_v2_design import design_v2, PALETTE


def area_only(g):
    if g.geom_type == 'Polygon':
        return g
    if hasattr(g, 'geoms'):
        return union_all([area_only(p) for p in g.geoms])
    return Polygon()


def printable_design():
    d = design_v2()
    a = d['masks']['black']
    visible = {}
    changes = {}
    for name in ('blue', 'red', 'ivory'):
        original = d['visible'][name]
        # 0.12 mm ink expansion, then an opening with a 0.8 mm diameter tool:
        # rounded tips, no needle ends, and larger calligraphy stroke cores.
        g = original.buffer(.12, quad_segs=4)
        g = g.buffer(-.4, quad_segs=4).buffer(.4, quad_segs=4)
        g = area_only(g.simplify(.008, preserve_topology=True).intersection(a))
        if name == 'ivory':
            # Open the calligraphy counters rather than leaving sub-nozzle
            # pinholes. This is a deliberate editable-font adaptation.
            counters = []
            parts = [g] if g.geom_type == 'Polygon' else g.geoms
            for p in parts:
                for ring in p.interiors:
                    hole = Polygon(ring)
                    x0,y0,x1,y1 = hole.bounds
                    if 37 < x0 < 63 and 35 < y0 < 46:
                        padding = max(0, (.64-min(x1-x0,y1-y0))/2)
                        counters.append(hole.buffer(padding, quad_segs=4))
            g = area_only(g.difference(union_all(counters)))
        visible[name] = g
        changes[name] = dict(original_area_mm2=original.area, final_area_mm2=g.area)
    w = visible['ivory']
    r = union_all([visible['red'], w])
    b = union_all([visible['blue'], r])
    # A few microns of hidden support avoid zero-width connections where
    # different drawing colors only meet at one vertex.
    b = area_only(set_precision(b.buffer(.006, quad_segs=4).intersection(a), .001))
    r = area_only(set_precision(r.buffer(.003, quad_segs=4).intersection(b), .001))
    w = area_only(set_precision(w.intersection(r), .001))
    # Clip without a precision grid once more: all higher bands are subsets.
    b = area_only(b.intersection(a, grid_size=0))
    r = area_only(r.intersection(b, grid_size=0))
    w = area_only(w.intersection(r, grid_size=0))
    d['masks'] = dict(black=a, blue=b, red=r, ivory=w)
    d['visible'] = dict(black=a.difference(b), blue=b.difference(r),
                        red=r.difference(w), ivory=w)
    d['magnets'] = []
    d['manufacturing_adjustments'] = changes
    d['status'] = 'Manufacturing geometry; validate actual exports before delivery'
    d['remaining_checks'] = ['Physical print and actual filament color match']
    return d
