#!/usr/bin/env python3
"""Run Bambu Studio CLI, verify its actual result/G-code, and package a preview.

Requires an installed Bambu Studio executable; model generation itself only
needs setup.sh. GUI thumbnail generation may be unavailable on cloud machines;
the package cover then comes from the actual-STL CPU renderer, not a GUI claim.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from shapely import LineString, box, union_all
from scripts.build_temple_v2 import OUT,NS,mesh_from_xml,xmlbytes
from src.validation import validate_mesh
from src.temple_v2_print import printable_design


def gcode_audit(text):
    heights=[];switches=[];segments=[];z=0.;x=y=0.;width=.42;feature=''
    # Official P1S profile compensates a (0,2) nozzle offset in commanded XY.
    # Restore MODEL coordinates before comparing paths to the design polygons.
    match=re.search(r'^; extruder_offset = ([^\n]+)',text,re.MULTILINE)
    assert match,'G-code must declare its nozzle offset'
    ox,oy=[float(v) for v in match[1].split(',')[0].split('x')]
    for line in text.splitlines():
        if line.startswith('; Z_HEIGHT:'):
            z=float(line.split(':')[1]);heights.append(z)
        elif line.startswith('; LINE_WIDTH:'):width=float(line.split(':')[1])
        elif line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
        elif re.match(r'^T[123]\s*$',line):switches.append(dict(tool=int(line[1:]),start_layer_z_mm=z))
        if re.match(r'^G[0123]\s',line):
            # Bambu emits compact valid numbers such as E.14568 and E-.02.
            p={k:float(v) for k,v in re.findall(r'([XYEIJ])(-?(?:\d+(?:\.\d*)?|\.\d+))',line.split(';')[0])}
            nx=p.get('X',x);ny=p.get('Y',y)
            points=[(x,y),(nx,ny)]
            if line.startswith(('G2 ','G3 ')) and ('I' in p or 'J' in p):
                cx,cy=x+p.get('I',0),y+p.get('J',0)
                radius=math.hypot(x-cx,y-cy)
                a=math.atan2(y-cy,x-cx);b=math.atan2(ny-cy,nx-cx)
                sweep=(b-a)%(2*math.pi) if line.startswith('G3 ') else -((a-b)%(2*math.pi))
                if abs(sweep)<1e-8:sweep=2*math.pi if line.startswith('G3 ') else -2*math.pi
                # <= 0.005mm chord sag; preserve native arc geometry in audit.
                steps=max(2,math.ceil(abs(sweep)/min(.15,math.sqrt(.04/max(radius,.001)))))
                points=[(cx+radius*math.cos(t),cy+radius*math.sin(t)) for t in np.linspace(a,a+sweep,steps+1)]
                points[0]=(x,y);points[-1]=(nx,ny)
            if p.get('E',0)>0 and (nx!=x or ny!=y) and feature not in ('Prime tower','Custom','Flush'):
                if 78-ox<=x<=178-ox and 78-ox<=nx<=178-ox and 91.84-oy<=y<=164.16-oy and 91.84-oy<=ny<=164.16-oy:
                    segments.append((z,[(px-78+ox,py-91.843+oy) for px,py in points],width))
            x,y=nx,ny
    assert len(heights)==20 and np.allclose(heights,np.arange(1,21)*.2)
    assert switches==[dict(tool=1,start_layer_z_mm=1.8),dict(tool=2,start_layer_z_mm=2.6),dict(tool=3,start_layer_z_mm=3.4)]
    # Check real final-layer extrusion reaches the three approved glyphs.
    roi=box(38,36,62,45)
    paths=union_all([LineString(xy).buffer(w/2,quad_segs=4) for h,xy,w in segments if abs(h-4)<1e-6]).intersection(roi)
    expected=printable_design()['masks']['ivory'].intersection(roi)
    ratio=paths.intersection(expected).area/expected.area
    assert ratio>.85,('Calligraphy path coverage too low',ratio)
    return dict(total_layers=20,layer_heights_mm=heights,color_changes=switches,
                commanded_nozzle_offset_mm=[ox,oy],
                plaque_final_layer_extrusion_coverage_fraction=ratio),segments


def native_audit(path,expected):
    ns={'m':NS};result={}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        settings=json.loads(z.read('Metadata/project_settings.config'))
        config=ET.fromstring(z.read('Metadata/model_settings.config'))
        assert model.get('unit')=='millimeter'
        assert settings['filament_colour']==['#202329','#24355C','#AF302B','#EAE0C9']
        assert settings['printer_model']=='Bambu Lab P1S'
        assert settings['layer_height']=='0.2' and settings['enable_support']=='0'
        for component in model.findall('m:resources/m:object/m:components/m:component',ns):
            ident=component.get('objectid')
            subpath=component.get('{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path').lstrip('/')
            sub=ET.fromstring(z.read(subpath))
            obj=sub.find(f'm:resources/m:object[@id="{ident}"]',ns)
            mesh=mesh_from_xml(obj,ns)
            values=np.array([float(v) for v in component.get('transform').split()])
            matrix=np.eye(4);matrix[:3,:]=values.reshape(4,3).T
            mesh.apply_transform(matrix)
            name=['black','blue','red','ivory'][int(ident)-1]
            result[name]=validate_mesh(mesh,expected_volume=expected[name],components=None)
            part=config.find(f'object/part[@id="{ident}"]')
            assert part.find('metadata[@key="extruder"]').get('value')==ident
            stats=part.find('mesh_stat')
            for key in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges']:
                assert stats.get(key)=='0',('Bambu changed geometry',ident,key)
        gcode=z.read('Metadata/plate_1.gcode').decode()
        audit,segments=gcode_audit(gcode)
    return result,audit,segments


def package_cover(src,dest):
    # Preserve all native Bambu model/settings/G-code bytes. Only supply the
    # thumbnail files referenced by Bambu when cloud GPU rendering is absent.
    with zipfile.ZipFile(src) as zi,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as zo:
        for name in zi.namelist():
            if name not in ['Metadata/plate_1.png','Metadata/plate_1_small.png']:
                zo.writestr(name,zi.read(name))
        im=Image.open(OUT/'preview/front_effect.png').convert('RGB')
        for size,name in [(512,'plate_1.png'),(128,'plate_1_small.png')]:
            cover=Image.new('RGB',(size,size),'white');thumb=im.copy();thumb.thumbnail((size,size))
            cover.paste(thumb,((size-thumb.width)//2,(size-thumb.height)//2))
            stream=io.BytesIO();cover.save(stream,format='PNG');zo.writestr('Metadata/'+name,stream.getvalue())


def path_preview(segments,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scripts.build_temple import plot_geometry
    from src.temple_v2_design import PALETTE
    fig,ax=plt.subplots(figsize=(10,7.7))
    for (name,color),height in zip(PALETTE.items(),[1.6,2.4,3.2,4.]):
        g=union_all([LineString(xy).buffer(w/2,quad_segs=3) for h,xy,w in segments if abs(h-height)<1e-6])
        plot_geometry(ax,g,color)
    ax.set_aspect('equal');ax.set(xlim=(-2,102),ylim=(-2,75));ax.axis('off')
    ax.set_title('Actual sliced extrusion paths / top layer of each color')
    fig.tight_layout();fig.savefig(out,dpi=160);plt.close(fig)


def finish(work,command=None):
    native=work/'temple_v2_P1S_AMS_sliced.3mf'
    result=json.loads((work/'result.json').read_text())
    assert result['return_code']==0,result
    plate=result['sliced_plates'][0]
    assert plate['filament_change_times']==3 and plate['warning_message']==''
    expected=json.loads((OUT/'validation.json').read_text())['expected_prism_volumes_mm3']
    dest=OUT/'3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf'
    package_cover(native,dest)
    geometry,audit,segments=native_audit(dest,expected)
    path_preview(segments,OUT/'preview/actual_sliced_paths.png')
    log=(work/'slice.log').read_text()
    diagnostics=[line for line in log.splitlines() if '[error]' in line]
    assert all(('Wayland:' in line or 'glfwInit' in line) for line in diagnostics),diagnostics
    report=dict(bambu_studio_version='02.08.02.61',printer='P1S / 0.4 mm / AMS',
                slicer_result=result,geometry_after_native_bambu_export=geometry,gcode_audit=audit,
                preview_note='Cloud GLFW/Wayland GUI thumbnail unavailable; covers are CPU renders of the actual validated STL solids. Slicing/export succeeded.',
                cloud_thumbnail_diagnostics=diagnostics,command=command,
                physical_print_tested=False,
                input_project_sha256=hashlib.sha256((OUT/'3mf/chenghuang_temple_v2_P1S_AMS.3mf').read_bytes()).hexdigest(),
                native_sliced_project_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    (OUT/'slicing_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'source/bambu_slice.log').write_text(log)
    print(json.dumps(audit,indent=2),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bambu',type=Path)
    ap.add_argument('--work-dir',type=Path,required=True)
    ap.add_argument('--existing-result',action='store_true')
    args=ap.parse_args();work=args.work_dir.resolve();work.mkdir(parents=True,exist_ok=True)
    command=None
    if not args.existing_result:
        if not args.bambu:ap.error('--bambu is required unless --existing-result')
        command=[str(args.bambu.resolve()),'--datadir',str(work/'settings'),'--debug','3',
                 '--slice','0','--skip-useless-pick','--export-3mf','temple_v2_P1S_AMS_sliced.3mf',
                 '--outputdir',str(work),str(OUT/'3mf/chenghuang_temple_v2_P1S_AMS.3mf')]
        p=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=600)
        (work/'slice.log').write_text(p.stdout+p.stderr)
        assert p.returncode==0
    finish(work,command)


if __name__=='__main__':main()
