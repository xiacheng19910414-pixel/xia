#!/usr/bin/env python3
"""Export the approved V2 as real OpenSCAD solids and a P1S/AMS 3MF project."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import trimesh
from src.temple_v2_print import printable_design
from src.temple_v2_design import PALETTE
from src.temple_design import Z_BANDS
from src.terrace_mesh import triangulated_plan, terrace_mesh, plan_volumes, partition_audit
from src.validation import validate_mesh, validate_file
from scripts.build_temple import plot_geometry, polygons, save_svg, mesh_from_xml, mesh_section_xy
from scripts.render_temple import render

OUT = ROOT / 'output/chenghuang_temple_v2_print'
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('', NS)


def xmlbytes(node):
    return ET.tostring(node, encoding='utf-8', xml_declaration=True)


def source_and_export(d, plan, out):
    lines = ['// Units: millimeters. Rear Z=0. NO magnet cavities.',
             '// Editable architecture: src/temple_v2_design.py; printable adaptation: src/temple_v2_print.py.',
             '// Regenerate with .venv/bin/python scripts/build_temple_v2.py',
             'part="assembly";']
    expected = plan_volumes(plan, False)
    for name in ['assembly', *PALETTE]:
        m = terrace_mesh(plan, False, None if name == 'assembly' else name)
        # Verify binSTL float32 coordinates BEFORE OpenSCAD writes the STL.
        probe = trimesh.Trimesh(vertices=m.vertices.astype(np.float32), faces=m.faces, process=False)
        validate_mesh(probe, expected_volume=expected[name], components=1 if name == 'assembly' else None)
        pts = [[round(float(x), 7) for x in row] for row in m.vertices]
        lines.append(f'module {name}() {{ polyhedron(points={json.dumps(pts,separators=(",",":"))},faces={json.dumps(m.faces[:,::-1].tolist(),separators=(",",":"))},convexity=30); }}')
    lines.append('if(part=="assembly") assembly();')
    for name, color in PALETTE.items():
        lines.append(f'else if(part=="{name}") color("{color}") {name}();')
    lines.append('else assert(false,"Unknown part");')
    scad = out / 'source/temple_v2.scad'
    scad.write_text('\n'.join(lines) + '\n')
    for what in ['masks', 'visible']:
        body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="{d["height"]}mm" viewBox="0 0 100 {d["height"]}">',
                f'<g transform="translate(0 {d["height"]}) scale(1 -1)">']
        for name, geom in d[what].items():
            for poly in polygons(geom):
                path = ' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in ring.coords)+' Z' for ring in [poly.exterior,*poly.interiors])
                body.append(f'<path fill="{PALETTE[name]}" fill-rule="evenodd" d="{path}"/>')
        (out/'source'/f'{what}.svg').write_text('\n'.join(body+['</g>','</svg>'])+'\n')
    logs = []
    jobs = [('assembly', 'temple_v2_complete.stl')]+[(n,f'band_{i+1}_{n}.stl') for i,n in enumerate(PALETTE)]
    jobs.append(('assembly','temple_v2_geometry.3mf'))
    for name, filename in jobs:
        dest = out / ('3mf' if filename.endswith('3mf') else 'stl') / filename
        cmd = ['openscad','--hardwarnings','-o',str(dest),'-D',f'part="{name}"',str(scad)]
        if filename.endswith('.stl'):cmd[1:1] = ['--export-format','binstl']
        print('OpenSCAD export', filename, flush=True)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           env={**os.environ,'QT_QPA_PLATFORM':'offscreen'})
        logs.append(dict(command=cmd,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        (out/'source/export_log.json').write_text(json.dumps(logs,indent=2)+'\n')
        if p.returncode or 'ERROR:' in p.stderr:raise RuntimeError(p.stderr)
    return expected


def previews(d, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(100/25.4,d['height']/25.4))
    ax = fig.add_axes([0,0,1,1])
    for i,(n,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[n],i)
    ax.set(xlim=(0,100),ylim=(0,d['height']));ax.set_aspect('equal');ax.axis('off')
    fig.savefig(out/'preview/front_actual_size.pdf')
    fig.savefig(out/'preview/front_four_colors.png',dpi=450,facecolor='white')
    save_svg(fig,out/'preview/front_four_colors.svg')
    plt.close(fig)
    fig,(ax,side) = plt.subplots(2,1,figsize=(11,10),gridspec_kw={'height_ratios':[3,1]})
    for i,(n,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[n],i)
    ax.set(xlim=(-5,108),ylim=(-6,d['height']+3));ax.set_aspect('equal');ax.axis('off')
    ax.annotate('',xy=(0,-3),xytext=(100,-3),arrowprops={'arrowstyle':'<->'})
    ax.text(50,-2.5,'100.000 mm',ha='center')
    ax.annotate('',xy=(104,0),xytext=(104,d['height']),arrowprops={'arrowstyle':'<->'})
    ax.text(105,d['height']/2,f'{d["height"]:.3f} mm',rotation=90)
    ax.set_title('Actual front geometry / four solid colors / NO magnet cavities')
    # True cross-section of this model at the plaque center.
    from shapely import LineString
    y = 40.
    for n,g in d['masks'].items():
        section = g.intersection(LineString([(-1,y),(101,y)]))
        for segment in (section.geoms if hasattr(section,'geoms') else [section]):
            if segment.geom_type != 'LineString':continue
            x0,_,x1,_ = segment.bounds
            lo,hi = Z_BANDS[n]
            side.add_patch(Rectangle((x0,lo),x1-x0,hi-lo,color=PALETTE[n],linewidth=0))
    for z in [0,1.6,2.4,3.2,4.]:
        side.axhline(z,color='#888',lw=.4,ls='--');side.text(101,z,f'{z:.1f} mm',va='center')
    side.set(xlim=(0,110),ylim=(-.4,5.5),xlabel='X / mm',ylabel='Z / mm',
             title='Actual X-Z section at Y=40 mm (vertical scale enlarged)')
    side.text(50,4.9,'P1S / 0.4 nozzle / 0.2 layers / 20 layers / 3 AMS color changes',ha='center',fontsize=9)
    fig.tight_layout();fig.savefig(out/'preview/dimensions_and_layers.png',dpi=160)
    save_svg(fig,out/'preview/dimensions_and_layers.svg');plt.close(fig)
    render(out,palette=PALETTE)
    render(out,tilt=32,azimuth=-8,palette=PALETTE)


def project_3mf(out, settings):
    e = lambda tag:'{'+NS+'}'+tag
    model = ET.Element(e('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'zh-CN'})
    for key,value in [('Title','Chenghuang Temple V2 / P1S AMS'),('BambuStudio:3mfVersion','1'),
                      ('Application','BambuStudio-02.08.02.61')]:
        ET.SubElement(model,e('metadata'),{'name':key}).text=value
    resources=ET.SubElement(model,e('resources'))
    mat=ET.SubElement(resources,e('basematerials'),{'id':'10'})
    for name,color in PALETTE.items():ET.SubElement(mat,e('base'),{'name':name,'displaycolor':color+'FF'})
    config=ET.Element('config')
    objconfig=ET.SubElement(config,'object',{'id':'5'})
    ET.SubElement(objconfig,'metadata',{'key':'name','value':'Chenghuang Temple V2 - 100mm'})
    ET.SubElement(objconfig,'metadata',{'key':'extruder','value':'1'})
    for i,name in enumerate(PALETTE,1):
        mesh=trimesh.load(out/'stl'/f'band_{i}_{name}.stl',force='mesh',process=False);mesh.merge_vertices()
        obj=ET.SubElement(resources,e('object'),{'id':str(i),'type':'model','name':name,'pid':'10','pindex':str(i-1)})
        mx=ET.SubElement(obj,e('mesh'));vertices=ET.SubElement(mx,e('vertices'))
        for v in mesh.vertices:ET.SubElement(vertices,e('vertex'),{k:f'{x:.7f}' for k,x in zip(('x','y','z'),v)})
        faces=ET.SubElement(mx,e('triangles'))
        for face in mesh.faces:ET.SubElement(faces,e('triangle'),{k:str(int(x)) for k,x in zip(('v1','v2','v3'),face)})
        part=ET.SubElement(objconfig,'part',{'id':str(i),'subtype':'normal_part'})
        lo,hi=Z_BANDS[name]
        for key,value in [('name',f'{i} {name} Z{lo}-{hi} mm'),('extruder',str(i)),
                          ('matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')]:
            ET.SubElement(part,'metadata',{'key':key,'value':value})
        ET.SubElement(part,'mesh_stat',{'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
    assembly=ET.SubElement(resources,e('object'),{'id':'5','type':'model','name':'Chenghuang Temple V2'})
    components=ET.SubElement(assembly,e('components'))
    for i in range(1,5):ET.SubElement(components,e('component'),{'objectid':str(i)})
    build=ET.SubElement(model,e('build'))
    # Center the original-coordinate assembly on the P1S 256mm bed.
    ET.SubElement(build,e('item'),{'objectid':'5','transform':'1 0 0 0 1 0 0 0 1 78 91.843 0','printable':'1'})
    plate=ET.SubElement(config,'plate')
    ET.SubElement(plate,'metadata',{'key':'plater_id','value':'1'})
    instance=ET.SubElement(plate,'model_instance')
    ET.SubElement(instance,'metadata',{'key':'object_id','value':'5'})
    ET.SubElement(instance,'metadata',{'key':'instance_id','value':'0'})
    content=ET.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    for ext,ctype in [('rels','application/vnd.openxmlformats-package.relationships+xml'),
                      ('model','application/vnd.ms-package.3dmanufacturing-3dmodel+xml'),
                      ('config','application/octet-stream'),('png','image/png')]:
        ET.SubElement(content,'Default',{'Extension':ext,'ContentType':ctype})
    rels=ET.Element('Relationships',xmlns='http://schemas.openxmlformats.org/package/2006/relationships')
    ET.SubElement(rels,'Relationship',{'Target':'/3D/3dmodel.model','Id':'rel0','Type':'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'})
    ET.SubElement(rels,'Relationship',{'Target':'/Metadata/plate_1.png','Id':'rel1','Type':'http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail'})
    dest=out/'3mf/chenghuang_temple_v2_P1S_AMS.3mf'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for name,node in [('[Content_Types].xml',content),('_rels/.rels',rels),
                          ('3D/3dmodel.model',model),('Metadata/model_settings.config',config)]:z.writestr(name,xmlbytes(node))
        z.writestr('Metadata/project_settings.config',json.dumps(settings,ensure_ascii=False,indent=2))
        z.write(out/'preview/front_effect.png','Metadata/plate_1.png')
    return dest


def validate_project(path,expected):
    ns={'m':NS};result={}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        config=ET.fromstring(z.read('Metadata/model_settings.config'))
        settings=json.loads(z.read('Metadata/project_settings.config'))
    assert model.get('unit')=='millimeter'
    assert settings['filament_colour']==list(PALETTE.values())
    assert settings['printer_model']=='Bambu Lab P1S'
    bases=model.findall('m:resources/m:basematerials/m:base',ns)
    assert [b.get('displaycolor') for b in bases]==[c+'FF' for c in PALETTE.values()]
    for i,name in enumerate(PALETTE,1):
        obj=model.find(f'm:resources/m:object[@id="{i}"]',ns)
        assert obj.get('pid')=='10' and obj.get('pindex')==str(i-1)
        assert config.find(f'object/part[@id="{i}"]/metadata[@key="extruder"]').get('value')==str(i)
        result[name]=validate_mesh(mesh_from_xml(obj,ns),expected_volume=expected[name],components=None)
    assert [c.get('objectid') for c in model.findall('m:resources/m:object[@id="5"]/m:components/m:component',ns)]==['1','2','3','4']
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--settings',type=Path,default=OUT/'source/P1S_AMS_project_settings.json')
    args=ap.parse_args()
    for sub in ['source','stl','3mf','preview']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    d=printable_design();plan=triangulated_plan(d)
    expected=source_and_export(d,plan,OUT)
    report={'planar_partition':partition_audit(plan),'bands':{},'nested_support':[],'actual_stl_sections':[]}
    report['assembly']=validate_file(OUT/'stl/temple_v2_complete.stl',expected_volume=expected['assembly'],
                                     expected_bounds=[[0,0,0],[100,72.314,4]])
    for i,name in enumerate(PALETTE,1):
        report['bands'][name]=validate_file(OUT/'stl'/f'band_{i}_{name}.stl',expected_volume=expected[name],components=None)
    for (n,a),(m,b) in zip(list(d['masks'].items()),list(d['masks'].items())[1:]):
        unsupported=b.difference(a).area
        assert unsupported<1e-5
        report['nested_support'].append(dict(lower=n,upper=m,unsupported_area_mm2=unsupported))
    mesh=trimesh.load(OUT/'stl/temple_v2_complete.stl',force='mesh',process=False);mesh.merge_vertices()
    for name,z in [('black',.8),('blue',2.),('red',2.8),('ivory',3.6)]:
        difference=mesh_section_xy(mesh,z).symmetric_difference(d['masks'][name]).area
        assert difference<.03,(name,difference)
        report['actual_stl_sections'].append(dict(name=name,z_mm=z,symmetric_difference_area_mm2=difference))
    with zipfile.ZipFile(OUT/'3mf/temple_v2_geometry.3mf') as z:
        xml=ET.fromstring(z.read('3D/3dmodel.model'))
    report['openscad_3mf']=validate_mesh(mesh_from_xml(xml.find('m:resources/m:object',{'m':NS}),{'m':NS}),expected_volume=expected['assembly'])
    previews(d,OUT)
    settings=json.loads(args.settings.read_text())
    path=project_3mf(OUT,settings)
    report['colored_project_3mf']=validate_project(path,expected)
    report['expected_prism_volumes_mm3']=expected
    report['physical_print_tested']=False
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    metadata={k:v for k,v in d.items() if k not in ('masks','visible')}
    metadata['status']='OpenSCAD exports and mesh/material validation completed; see validation.json and slicing report'
    metadata['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/temple_v2_design.py','src/temple_v2_print.py','src/terrace_mesh.py','assets/fonts/mashanzheng/MaShanZheng-Regular.ttf']}
    (OUT/'design.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report['assembly'],indent=2),flush=True)


if __name__=='__main__':main()
