"""Construct a true manifold terraced solid from a common constrained XY mesh.

All color boundaries and cavity circles share one noded planar subdivision.
Height differences create outside walls, never overlapping internal prisms.
This avoids near-coplanar CSG slivers when touching extrusions are unioned.
"""
import numpy as np
import trimesh
from shapely import Polygon, Point, LineString, constrained_delaunay_triangles, union_all
from shapely.ops import polygonize
from src.temple_design import Z_BANDS
from src.validation import validate_mesh


def triangulated_plan(d):
    boundaries=[g.boundary for g in d['masks'].values()]
    for m in d['magnets']:
        boundaries.append(Point(m['x'],m['y']).buffer(4.1,quad_segs=24).boundary)
    graph=union_all(boundaries,grid_size=.001)
    vertices=[];indices={};triangles=[];heights=[];cavities=[]
    for cell in polygonize(graph):
        point=cell.representative_point()
        if not d['masks']['black'].covers(point):continue
        h=1.6
        for name,g in d['masks'].items():
            if g.covers(point):h=Z_BANDS[name][1]
        cavity=any(point.distance(Point(m['x'],m['y']))<4.1-1e-7 for m in d['magnets'])
        for tri in constrained_delaunay_triangles(cell).geoms:
            coordinates=list(tri.exterior.coords)[:3]
            if not tri.area>1e-10:raise ValueError('Degenerate planar cell')
            face=[]
            for xy in coordinates:
                xy=tuple(round(v,7) for v in xy)
                if xy not in indices:indices[xy]=len(vertices);vertices.append(xy)
                face.append(indices[xy])
            a,b,c=np.array([vertices[i] for i in face])
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:face=face[::-1]
            triangles.append(face);heights.append(h);cavities.append(cavity)
    return np.array(vertices),np.array(triangles),np.array(heights),np.array(cavities)


def terrace_mesh(plan,slots=True,band=None):
    xy,triangles,h,cavity=plan
    floors=np.where(cavity & slots,2.2,0.)
    if band:
        z0,z1=Z_BANDS[band]
        floors=np.maximum(floors,z0)
        h=np.minimum(h,z1)
    active=h>floors+1e-6
    verts=[];index={};faces=[]
    def vert(i,z):
        p=(float(xy[i,0]),float(xy[i,1]),round(float(z),5))
        if p not in index:index[p]=len(verts);verts.append(p)
        return index[p]
    edges={}
    for t,(face,valid) in enumerate(zip(triangles,active)):
        if not valid:continue
        a,b,c=face
        faces.append([vert(a,h[t]),vert(b,h[t]),vert(c,h[t])])
        faces.append([vert(c,floors[t]),vert(b,floors[t]),vert(a,floors[t])])
        for a,b in [(a,b),(b,c),(c,a)]:
            key=tuple(sorted((a,b)))
            edges.setdefault(key,[]).append((t,a,b))
    # Outside-oriented vertical quads, subdivided at every Z level so adjacent
    # wall faces cannot form T-junctions at a terrace or cavity transition.
    levels=[0.,1.6,2.2,2.4,3.2,4.]
    def wall(a,b,z0,z1):
        steps=sorted(set([float(z0),float(z1)]+[z for z in levels if z0<z<z1]))
        for lo,hi in zip(steps,steps[1:]):
            # Active triangle is to the left of a->b, so outside is right.
            v0,v1,v2,v3=vert(a,lo),vert(b,lo),vert(b,hi),vert(a,hi)
            faces.extend([[v0,v1,v2],[v0,v2,v3]])
    for owners in edges.values():
        if len(owners)>2:raise ValueError('Nonmanifold planar subdivision')
        t,a,b=owners[0]
        if len(owners)==1:
            wall(a,b,floors[t],h[t]);continue
        u,_,_=owners[1]
        if h[t]>h[u]+1e-7:wall(a,b,h[u],h[t])
        if h[u]>h[t]+1e-7:wall(b,a,h[t],h[u])
        if floors[t]<floors[u]-1e-7:wall(a,b,floors[t],floors[u])
        if floors[u]<floors[t]-1e-7:wall(b,a,floors[u],floors[t])
    mesh=trimesh.Trimesh(vertices=np.array(verts),faces=np.array(faces),process=False)
    mesh.merge_vertices()
    validate_mesh(mesh,components=None)
    return mesh


def plan_volumes(plan,slots=True):
    """Analytic prism volumes on the EXACT 1 µm-noded construction plan.

    Independent of signed mesh-face integration used by trimesh validation.
    """
    xy,triangles,h,cavity=plan
    t=xy[triangles]
    u=t[:,1]-t[:,0];v=t[:,2]-t[:,0]
    areas=np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
    floor=np.where(cavity & slots,2.2,0.)
    result={'assembly':float(np.sum(areas*(h-floor)))}
    for name,(z0,z1) in Z_BANDS.items():
        result[name]=float(np.sum(areas*np.maximum(0,np.minimum(h,z1)-np.maximum(floor,z0))))
    return result


def partition_audit(plan):
    """Prove the heightfield's XY triangles are a non-overlapping partition.

    A monotone solid over a non-crossing planar partition has no crossing
    faces; terrace_mesh also checks its complete 3D surface topology.
    """
    xy,triangles,h,cavity=plan
    polys=[Polygon(xy[face]) for face in triangles]
    footprint=union_all(polys)
    overlap=sum(p.area for p in polys)-footprint.area
    if abs(overlap)>1e-6 or not footprint.is_valid:
        raise ValueError('Overlapping or invalid planar construction')
    if np.any(np.where(cavity,2.2,0)>=h):
        raise ValueError('Cavity crosses the front surface')
    return dict(triangles=len(triangles),footprint_area_mm2=footprint.area,
                overlap_area_mm2=float(overlap),valid_partition=True,
                method='Non-overlapping constrained XY triangulation with monotone solid Z intervals; full surface topology checked independently')
