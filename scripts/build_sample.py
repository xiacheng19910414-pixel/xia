#!/usr/bin/env python3
"""Render actual OpenSCAD solids, validate STL/3MF, and preview those STL meshes."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import trimesh
from src.validation import validate_file, validate_mesh

COLORS = {'base':'#4169e1','red':'#ff0000','yellow':'#ffd700',
          'green':'#32cd32','blue':'#4169e1'}
POSITIONS = {'red':(0,1),'yellow':(1,1),'green':(0,0),'blue':(1,0)}


def read_3mf(path):
    """Strictly decode the single-solid OpenSCAD 3MF, including its mm unit.

    Fail on unsupported structures, instead of silently ignoring transforms/parts.
    """
    ns = {'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('Corrupt 3MF archive')
        model = ET.fromstring(z.read('3D/3dmodel.model'))
    if model.get('unit', 'millimeter') != 'millimeter':
        raise ValueError('3MF is not in mm')
    objects = model.findall('m:resources/m:object',ns)
    items = model.findall('m:build/m:item',ns)
    if len(objects) != 1 or len(items) != 1:
        raise ValueError('Expected one 3MF object and build item')
    if items[0].get('objectid') != objects[0].get('id') or items[0].get('transform'):
        raise ValueError('Unsupported 3MF reference/transform')
    vertices = objects[0].findall('m:mesh/m:vertices/m:vertex',ns)
    faces = objects[0].findall('m:mesh/m:triangles/m:triangle',ns)
    mesh = trimesh.Trimesh(
        vertices=[[float(v.get(k)) for k in ('x','y','z')] for v in vertices],
        faces=[[int(f.get(k)) for k in ('v1','v2','v3')] for f in faces], process=False)
    mesh.merge_vertices()
    return mesh


def preview(out):
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from shapely import Polygon, union_all
    fig, ax = plt.subplots(figsize=(10,7))
    # A true orthographic top projection of the upward-facing STL triangles.
    # Draw by actual Z height: avoids painter-sort occlusion of large base faces.
    meshes = []
    for part,color in COLORS.items():
        mesh = trimesh.load(out/'stl'/f'{part}.stl',force='mesh')
        meshes.append((float(mesh.bounds[1,2]), mesh, color))
    for z,mesh,color in sorted(meshes,key=lambda item:item[0]):
        top = mesh.triangles[mesh.face_normals[:,2] > .5,:,:2]
        ax.add_collection(PolyCollection(top,facecolor=color,edgecolor=color,zorder=z))
        outline = union_all([Polygon(triangle) for triangle in top])
        polygons = list(outline.geoms) if outline.geom_type == 'MultiPolygon' else [outline]
        for polygon in polygons:
            for ring in [polygon.exterior, *polygon.interiors]:
                ax.plot(*ring.xy,color='#333333',linewidth=.7,zorder=z+.01)
    overall = trimesh.load(out/'stl'/'assembly.stl',force='mesh')
    x,y,z = overall.extents
    ax.set(xlim=(-3,x+3),ylim=(-3,y+3),xlabel='X (mm)',ylabel='Y (mm)',
           title=f'Four-color FDM magnet — STL top view\n{x:g} × {y:g} × {z:g} mm overall')
    ax.set_aspect('equal')
    fig.savefig(out/'preview'/'magnet.png',dpi=160,bbox_inches='tight')
    plt.close(fig)


def build(out, width=100., height=70., base=2., decor=1., extra=True):
    if not np.isfinite([width,height,base,decor]).all() or min(width,height)<=10 or min(base,decor)<=0:
        raise ValueError('Dimensions must be finite; width/height >10 mm, thicknesses >0')
    out = Path(out).resolve()
    for d in ('stl','3mf','preview'):
        (out/d).mkdir(parents=True,exist_ok=True)
    scad = out/'magnet.scad'
    # Standalone, editable, and includes this run's defaults.
    source = (ROOT/'src'/'magnet.scad').read_text()
    for name,value in [('width',width),('height',height),('base_thickness',base),('decor_height',decor)]:
        source = re.sub(rf'(?m)^{name} = [^;]+;',f'{name} = {value:g};',source)
    scad.write_text(source)
    env = {**os.environ,'QT_QPA_PLATFORM':'offscreen'}
    commands = []
    def render(part,dest):
        cmd = ['openscad','--hardwarnings','-o',str(dest),'-D',f'part="{part}"',str(scad)]
        commands.append(cmd)
        run = subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=180)
        if run.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
            raise RuntimeError(f'OpenSCAD export failed: {cmd}\n{run.stdout}\n{run.stderr}')
    pw,ph = (width-10)/2,(height-10)/2
    tile_volume = pw*ph*decor
    overall_bounds = [[0,0,0],[width,height,base+decor]]
    specs = {'base':dict(bounds=[[0,0,0],[width,height,base]],volume=width*height*base)}
    for part,(ix,iy) in POSITIONS.items():
        x,y = 4+ix*(pw+2),4+iy*(ph+2)
        specs[part] = dict(bounds=[[x,y,base],[x+pw,y+ph,base+decor]],volume=tile_volume)
    specs['assembly'] = dict(bounds=overall_bounds,volume=width*height*base+4*tile_volume)
    report = {'units':'mm','parts':{},'commands':commands}
    for part,spec in specs.items():
        dest = out/'stl'/f'{part}.stl'
        render(part,dest)
        report['parts'][part] = validate_file(dest,expected_bounds=spec['bounds'],expected_volume=spec['volume'])
    if extra:
        dest = out/'3mf'/'assembly.3mf'
        render('assembly',dest)
        report['3mf'] = validate_mesh(read_3mf(dest),expected_bounds=overall_bounds,
                                      expected_volume=specs['assembly']['volume'])
        preview(out)
        from PIL import Image
        with Image.open(out/'preview'/'magnet.png') as im:
            im.verify()
        report['preview'] = 'preview/magnet.png (rendered from exported STL meshes)'
    manifest = dict(units='mm',width=width,height=height,base_thickness=base,decor_height=decor,
                    origin='Lower left of base; Z=0 build plate',
                    parts={p:dict(file=f'stl/{p}.stl',color_hex=c,**specs[p]) for p,c in COLORS.items()},
                    instructions='Keep original coordinates for multi-material assembly. For separate printing, lower each decorative part to Z=0. Base shares blue material; four unique colors total. 3MF is fused geometry only; assign STL materials in slicer.')
    (out/'assembly.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    parser.add_argument('--width',type=float,default=100.)
    parser.add_argument('--height',type=float,default=70.)
    parser.add_argument('--base',type=float,default=2.)
    parser.add_argument('--decor',type=float,default=1.)
    parser.add_argument('--no-extras',action='store_true',help='Skip optional PNG and 3MF')
    args = parser.parse_args()
    result = build(args.output,args.width,args.height,args.base,args.decor,not args.no_extras)
    print(json.dumps(result,indent=2))
