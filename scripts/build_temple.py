#!/usr/bin/env python3
"""Build and verify the Chenghuang temple, not a picture pretending to be a model."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import numpy as np
import trimesh
from shapely import Polygon, Point, union_all
from shapely.geometry.polygon import orient
from src.temple_design import design, PALETTE, Z_BANDS
from src.validation import validate_file,validate_mesh

DEFAULT=ROOT/'output'/'chenghuang_temple'


def save_svg(fig,path,**kwargs):
    fig.savefig(path,**kwargs)
    # Matplotlib adds trailing blanks to SVG path lines. Keep review diffs clean.
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type=='Polygon':
        return [geom]
    if geom.geom_type=='MultiPolygon':
        return list(geom.geoms)
    raise ValueError(f'Not polygonal: {geom.geom_type}')


def scad_polygon(g):
    points=[]
    paths=[]
    for ring in [g.exterior,*g.interiors]:
        coords=list(ring.coords)[:-1]
        paths.append(list(range(len(points),len(points)+len(coords))))
        points.extend([[round(x,4),round(y,4)] for x,y in coords])
    return f'polygon(points={json.dumps(points,separators=(",",":"))},paths={json.dumps(paths,separators=(",",":"))});'


def write_source(d,out):
    from src.terrace_mesh import triangulated_plan,terrace_mesh
    plan=triangulated_plan(d)
    lines=['// Millimeters. Front is +Z, rear face Z=0.',
        '// Exact manifold terrace mesh generated from editable src/temple_design.py.',
        '// All source polygons are also available in visible.svg and masks.svg.',
        '// Four physical colors are assigned by Z bands, not per-layer tool changes.',
        'part="assembly";', 'magnet_slots=true;', '$fn=96;']
    def add_mesh(name,mesh):
        points=[[round(float(v),7) for v in p] for p in mesh.vertices]
        # OpenSCAD polyhedron uses the opposite face winding to trimesh/STL.
        # Reverse each face on input; no triangles are repaired or removed.
        lines.append(f'module {name}() {{ polyhedron(points={json.dumps(points,separators=(",",":"))},faces={json.dumps(mesh.faces[:,::-1].tolist(),separators=(",",":"))},convexity=30); }}')
    for slots in [True,False]:
        suffix='slots' if slots else 'plain'
        add_mesh('assembly_'+suffix,terrace_mesh(plan,slots))
        for name in Z_BANDS:
            if not slots and name in ('red','ivory'):continue
            add_mesh(name+'_'+suffix,terrace_mesh(plan,slots,name))
    lines.extend(['module coupon() { difference() { cube([50,20,4]);',
                  'translate([9,10,-0.01]) cylinder(d=8.0,h=2.21);',
                  'translate([25,10,-0.01]) cylinder(d=8.2,h=2.21);',
                  'translate([41,10,-0.01]) cylinder(d=8.4,h=2.21);','} }',
                  'if(part=="coupon") coupon();'])
    lines.append('else if(part=="assembly") { if(magnet_slots) assembly_slots(); else assembly_plain(); }')
    for name in Z_BANDS:
        plain=name+'_slots' if name in ('red','ivory') else name+'_plain'
        lines.append(f'else if(part=="{name}") color("{PALETTE[name]}") {{ if(magnet_slots) {name}_slots(); else {plain}(); }}')
    lines.append('else assert(false,"Unknown part");')
    (out/'source'/'temple.scad').write_text('\n'.join(lines)+'\n')
    # Human-readable editable 2D vector sources, including all color masks.
    for what in ('visible','masks'):
        svg_header=f'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="{d["height"]:.3f}mm" viewBox="0 0 100 {d["height"]:.3f}">'
        body=[svg_header,f'<g transform="translate(0 {d["height"]}) scale(1 -1)">']
        for name,g in d[what].items():
            for p in polygons(g):
                path=[]
                for ring in [p.exterior,*p.interiors]:
                    pts=list(ring.coords)
                    path.append('M'+' L'.join(f'{x:.4f},{y:.4f}' for x,y in pts)+' Z')
                body.append(f'<path fill="{PALETTE[name]}" fill-rule="evenodd" d="{" ".join(path)}"/>')
        body.extend(['</g>','</svg>'])
        (out/'source'/f'{what}.svg').write_text('\n'.join(body))


def plot_geometry(ax,g,color,zorder=1):
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    for poly in polygons(g):
        p=orient(poly,sign=1.)
        verts=[];codes=[]
        for ring in [p.exterior,*p.interiors]:
            coords=list(ring.coords)
            verts.extend(coords)
            codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(coords)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor='none',zorder=zorder))


def front_preview(d,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,7.5))
    for i,(name,g) in enumerate(d['masks'].items()):
        plot_geometry(ax,g,PALETTE[name],i+1)
    ax.set_aspect('equal');ax.set_xlim(-3,103);ax.set_ylim(-3,d['height']+3);ax.axis('off')
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    fig.savefig(out/'preview'/'front_four_colors.png',dpi=200,transparent=False,facecolor='white')
    save_svg(fig,out/'preview'/'front_four_colors.svg',transparent=True)
    plt.close(fig)
    # Physical 1:1 PDF page: print at actual size, without fit-to-page scaling.
    fig=plt.figure(figsize=(100/25.4,d['height']/25.4))
    ax=fig.add_axes([0,0,1,1])
    for i,(name,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[name],i+1)
    ax.set_xlim(0,100);ax.set_ylim(0,d['height']);ax.set_aspect('equal');ax.axis('off')
    fig.savefig(out/'preview'/'front_actual_size.pdf',metadata={'Title':'100 mm wide / actual-size print proof'})
    plt.close(fig)


def structural_preview(d,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,(front,side)=plt.subplots(2,1,figsize=(12,11),gridspec_kw={'height_ratios':[2.2,1]})
    for i,(name,g) in enumerate(d['masks'].items()):
        plot_geometry(front,g,PALETTE[name],i+1)
    front.set_aspect('equal');front.set_xlim(-7,107);front.set_ylim(-7,d['height']+6)
    front.set_title('Front dimensions and rear magnet locations (mm)',fontsize=15)
    front.annotate('',xy=(0,-3),xytext=(100,-3),arrowprops=dict(arrowstyle='<->'))
    front.text(50,-2.5,'100.00 mm',ha='center',va='bottom')
    front.annotate('',xy=(104,0),xytext=(104,d['height']),arrowprops=dict(arrowstyle='<->'))
    front.text(105,d['height']/2,f'{d["height"]:.3f} mm',rotation=90,va='center')
    for m in d['magnets']:
        circle=plt.Circle((m['x'],m['y']),m['diameter']/2,fill=False,edgecolor='#E6459F',linewidth=1.4,linestyle='--',zorder=8)
        front.add_patch(circle)
        front.text(m['x'],m['y']-8,f'({m["x"]:.2f}, {m["y"]:.2f})',ha='center',fontsize=9,zorder=9)
    front.axis('off')
    # Exact local X-Z section across both magnet centers; ivory pedestals provide 4 mm.
    y=d['magnets'][0]['y']
    from shapely import LineString
    for name,g in d['masks'].items():
        sec=g.intersection(LineString([(-1,y),(101,y)]))
        segments=list(sec.geoms) if hasattr(sec,'geoms') else [sec]
        z0,z1=Z_BANDS[name]
        for seg in segments:
            if seg.geom_type!='LineString':continue
            x0,_,x1,_=seg.bounds
            side.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,facecolor=PALETTE[name],edgecolor='#555',lw=.35))
    for m in d['magnets']:
        side.add_patch(Rectangle((m['x']-4.1,0),8.2,2.2,facecolor='white',edgecolor='#E6459F',lw=1.2))
        side.annotate('8.2 mm diameter / 2.2 mm deep',xy=(m['x'],1.1),xytext=(m['x'],-2.1),ha='center',fontsize=9,arrowprops=dict(arrowstyle='->',color='#E6459F'))
        side.annotate('',xy=(m['x']+3.0,2.2),xytext=(m['x']+3.,4.),arrowprops=dict(arrowstyle='<->',color='#E6459F'))
    side.text(50,5.0,'Roof above each cavity: 1.8 mm (>= 1.2 mm)',ha='center')
    for z in [0,1.6,2.4,3.2,4]:
        side.axhline(z,color='#888',lw=.3,ls='--');side.text(101,z,f'{z:.1f} mm',va='center',fontsize=9)
    side.set(xlim=(0,109),ylim=(-3,6.5),xlabel='X (mm)',ylabel='Z (mm)',title=f'Actual section at Y={y:.3f} mm; rear face Z=0; relief thickness shown enlarged vertically')
    fig.tight_layout()
    fig.savefig(out/'preview'/'dimensions_and_layers.png',dpi=160)
    save_svg(fig,out/'preview'/'dimensions_and_layers.svg')
    plt.close(fig)


def export_meshes(d,out):
    logs=out/'source'/'export_log.txt'
    records=[]
    specs=[('assembly','temple_with_slots.stl',True),('assembly','temple_no_slots.stl',False)]
    specs.extend((name,f'band_{i+1}_{name}.stl',True) for i,name in enumerate(Z_BANDS))
    specs.extend([('coupon','magnet_fit_coupon.stl',False),('assembly','temple_geometry.3mf',True)])
    for part,name,slots in specs:
        folder='3mf' if name.endswith('.3mf') else 'stl'
        dest=out/folder/name
        cmd=['openscad','--hardwarnings','-o',str(dest),'-D',f'part="{part}"','-D',f'magnet_slots={str(slots).lower()}',str(out/'source'/'temple.scad')]
        if name.endswith('.stl'):
            cmd[1:1]=['--export-format','binstl']
        print('EXPORT',name,flush=True)
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=600,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'})
        records.append(dict(command=cmd,exit_code=run.returncode,stdout=run.stdout,stderr=run.stderr))
        logs.write_text(json.dumps(records,indent=2))
        if run.returncode or 'ERROR:' in run.stderr or not dest.exists() or dest.stat().st_size==0:
            raise RuntimeError(f'Export failed: {name}\n{run.stderr}')
    return records


def read_single_3mf(path):
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        model=ET.fromstring(z.read('3D/3dmodel.model'))
    assert model.get('unit','millimeter')=='millimeter'
    objects=model.findall('m:resources/m:object',ns)
    assert len(objects)==1
    return mesh_from_xml(objects[0],ns)


def mesh_from_xml(obj,ns):
    verts=[[float(v.get(k)) for k in ('x','y','z')] for v in obj.findall('m:mesh/m:vertices/m:vertex',ns)]
    faces=[[int(t.get(k)) for k in ('v1','v2','v3')] for t in obj.findall('m:mesh/m:triangles/m:triangle',ns)]
    mesh=trimesh.Trimesh(vertices=verts,faces=faces,process=False)
    mesh.merge_vertices()
    return mesh


def colored_3mf(out):
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    ET.register_namespace('',ns)
    def e(name):return '{'+ns+'}'+name
    model=ET.Element(e('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'zh-CN'})
    ET.SubElement(model,e('metadata'),{'name':'Title'}).text='Chenghuang temple / four Z bands / 100 mm'
    resources=ET.SubElement(model,e('resources'))
    materials=ET.SubElement(resources,e('basematerials'),{'id':'10'})
    for name,color in PALETTE.items():
        ET.SubElement(materials,e('base'),{'name':name,'displaycolor':color+'FF'})
    for i,name in enumerate(PALETTE):
        mesh=trimesh.load(out/'stl'/f'band_{i+1}_{name}.stl',force='mesh',process=False)
        mesh.merge_vertices()
        obj=ET.SubElement(resources,e('object'),{'id':str(i+1),'type':'model','name':name,'pid':'10','pindex':str(i)})
        element=ET.SubElement(obj,e('mesh'))
        vertices=ET.SubElement(element,e('vertices'))
        for v in mesh.vertices:
            ET.SubElement(vertices,e('vertex'),dict(zip(('x','y','z'),(f'{x:.6f}' for x in v))))
        triangles=ET.SubElement(element,e('triangles'))
        for f in mesh.faces:
            ET.SubElement(triangles,e('triangle'),dict(zip(('v1','v2','v3'),(str(int(x)) for x in f))))
    assembly=ET.SubElement(resources,e('object'),{'id':'5','type':'model','name':'complete_temple'})
    comp=ET.SubElement(assembly,e('components'))
    for i in range(1,5):ET.SubElement(comp,e('component'),{'objectid':str(i)})
    build=ET.SubElement(model,e('build'))
    ET.SubElement(build,e('item'),{'objectid':'5'})
    path=out/'3mf'/'temple_four_bands.3mf'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
    return path


def verify_colored_3mf(path,expected):
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        assert z.read('_rels/.rels') and z.read('[Content_Types].xml')
    assert model.get('unit')=='millimeter'
    materials=model.findall('m:resources/m:basematerials/m:base',ns)
    assert [m.get('displaycolor') for m in materials]==[c+'FF' for c in PALETTE.values()]
    assert model.find('m:build/m:item',ns).get('objectid')=='5'
    objects={o.get('id'):o for o in model.findall('m:resources/m:object',ns)}
    assert [c.get('objectid') for c in objects['5'].findall('m:components/m:component',ns)]==['1','2','3','4']
    results={}
    for i,name in enumerate(PALETTE):
        obj=objects[str(i+1)]
        assert obj.get('pid')=='10' and obj.get('pindex')==str(i)
        mesh=mesh_from_xml(obj,ns)
        results[name]=validate_mesh(mesh,expected_volume=expected[name]['volume_mm3'],expected_bounds=expected[name]['bounds_mm'],components=expected[name]['components'])
    return results


def mesh_section_xy(mesh,z):
    section=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
    if section is None:raise ValueError(f'Empty section at {z}')
    result=Polygon()
    for loop in section.discrete:
        if not np.allclose(loop[0],loop[-1],atol=1e-5):
            raise ValueError('Open section contour')
        p=Polygon(loop[:,:2])
        if not p.is_valid:raise ValueError('Self-intersecting section')
        result=result.symmetric_difference(p)
    return result


def verify_sections(d,out):
    mesh=trimesh.load(out/'stl'/'temple_with_slots.stl',force='mesh')
    result=[]
    for name,z in [('black',.8),('blue',2.0),('blue',2.3),('red',2.8),('ivory',3.6)]:
        expected=d['masks'][name]
        if z<2.2:
            for m in d['magnets']:
                expected=expected.difference(Point(m['x'],m['y']).buffer(4.1,quad_segs=24))
        actual=mesh_section_xy(mesh,z)
        error=actual.symmetric_difference(expected).area
        if error>.03:raise ValueError(f'Incorrect actual cross-section at {z}: {error} mm²')
        result.append(dict(z_mm=z,color=name,symmetric_difference_area_mm2=error))
    return result


def geometry_checks(d,out):
    from src.terrace_mesh import triangulated_plan,plan_volumes,partition_audit
    plan=triangulated_plan(d)
    volumes=plan_volumes(plan,True)
    plain_volumes=plan_volumes(plan,False)
    hole_area=96/2*(4.1**2)*math.sin(2*math.pi/96)
    band_reports={}
    for i,(name,g) in enumerate(d['masks'].items()):
        z0,z1=Z_BANDS[name]
        # Each source mask component becomes exactly one closed extruded solid.
        volume=volumes[name]
        x0,y0,x1,y1=g.bounds
        band_reports[name]=validate_file(out/'stl'/f'band_{i+1}_{name}.stl',
                         expected_volume=volume,expected_bounds=[[x0,y0,z0],[x1,y1,z1]],components=len(polygons(g)))
    bounds=[[0,0,0],[100,d['height'],4]]
    expected_no=plain_volumes['assembly']
    expected_slots=volumes['assembly']
    ideal_no=sum(g.area*(Z_BANDS[n][1]-Z_BANDS[n][0]) for n,g in d['masks'].items())
    assert abs(expected_no-ideal_no)<.12, 'Planar construction deviates from design masks'
    full=validate_file(out/'stl'/'temple_with_slots.stl',expected_bounds=bounds,expected_volume=expected_slots)
    no_slots=validate_file(out/'stl'/'temple_no_slots.stl',expected_bounds=bounds,expected_volume=expected_no)
    geom3mf=validate_mesh(read_single_3mf(out/'3mf'/'temple_geometry.3mf'),expected_bounds=bounds,expected_volume=expected_slots)
    coupon_expected=50*20*4-sum(96/2*(diam/2)**2*math.sin(2*math.pi/96)*2.2 for diam in [8,8.2,8.4])
    coupon=validate_file(out/'stl'/'magnet_fit_coupon.stl',expected_bounds=[[0,0,0],[50,20,4]],expected_volume=coupon_expected)
    colored=verify_colored_3mf(out/'3mf'/'temple_four_bands.3mf',band_reports)
    support=[]
    names=list(d['masks'])
    for lower,upper in zip(names,names[1:]):
        delta=d['masks'][upper].difference(d['masks'][lower]).area
        assert delta<1e-5, (lower,upper,delta)
        support.append(dict(lower=lower,upper=upper,unsupported_area_mm2=delta))
    magnets=[]
    for m in d['magnets']:
        # Clearance around the entire cavity, including the 1.2 mm side-wall band.
        assert d['masks']['ivory'].covers(Point(m['x'],m['y']).buffer(4.1+1.2))
        magnets.append(dict(**m,roof_thickness_mm=1.8,minimum_wall_checked_mm=1.2,bridge_span_mm=8.2))
    return dict(units='mm',bounds_mm=bounds,with_slots=full,no_slots=no_slots,
                bands=band_reports,geometry_3mf=geom3mf,colored_3mf=colored,coupon=coupon,
                nested_support=support,actual_stl_sections=verify_sections(d,out),magnets=magnets,
                planar_partition=partition_audit(plan),
                color_count=4,layer_height_mm=.2,layer_count=20,
                xy_construction_grid_mm=.001,analytic_plan_volumes_mm3=volumes,
                pre_quantization_volume_mm3=ideal_no,quantization_volume_delta_mm3=expected_no-ideal_no,
                pauses_after_layers=[8,12,16],
                caveats=['Four band files intentionally contain multiple planar islands supported by lower bands; do not print separately.',
                         '8.2 mm cavity roofs require bridging or a slicer support plan; not physically print-tested.',
                         'Geometric validity and nesting do not replace a slicer preview or a physical print.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=DEFAULT)
    p.add_argument('--design-only',action='store_true')
    args=p.parse_args();out=args.output.resolve()
    for folder in ['stl','3mf','preview','source']:(out/folder).mkdir(parents=True,exist_ok=True)
    d=design();write_source(d,out);front_preview(d,out);structural_preview(d,out)
    manifest={k:v for k,v in d.items() if k not in ('masks','visible','letters')}
    manifest['palette']=PALETTE;manifest['z_bands_mm']=Z_BANDS
    manifest['font_ink_height_mm']=max(g.bounds[3]-g.bounds[1] for g in d['letters'])
    manifest['font_letter_heights_mm']=[g.bounds[3]-g.bounds[1] for g in d['letters']]
    manifest['nominal_detail_widths_mm']={'tile_gaps':.8,'brackets':1.05,'door_gaps':.8,'plaque_frame':.8,'text_counter_minimum':.62,'main_posts':2.4,'eave_band':1.9}
    import hashlib
    manifest['design_source_sha256']=hashlib.sha256((ROOT/'src'/'temple_design.py').read_bytes()).hexdigest()
    manifest['mesh_source_sha256']=hashlib.sha256((ROOT/'src'/'terrace_mesh.py').read_bytes()).hexdigest()
    (out/'design.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    if not args.design_only:
        export_meshes(d,out)
        colored_3mf(out)
        report=geometry_checks(d,out)
        (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()
