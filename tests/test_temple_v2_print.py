"""Validate real V2 OpenSCAD exports AND the native P1S/AMS sliced project."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pytest
from PIL import Image
from shapely import Polygon,box
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.validation import validate_file
from src.temple_v2_print import printable_design
from scripts.build_temple_v2 import OUT,validate_project,polygons
from scripts.slice_temple_v2 import native_audit


@pytest.fixture(scope='module')
def final():
    d=printable_design()
    r=json.loads((OUT/'validation.json').read_text())
    s=json.loads((OUT/'slicing_validation.json').read_text())
    meta=json.loads((OUT/'design.json').read_text())
    for p,h in meta['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'Rebuild stale V2 geometry'
    assert hashlib.sha256((OUT/'3mf/chenghuang_temple_v2_P1S_AMS.3mf').read_bytes()).hexdigest()==s['input_project_sha256']
    assert hashlib.sha256((OUT/'3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf').read_bytes()).hexdigest()==s['native_sliced_project_sha256']
    return d,r,s


def test_v2_actual_complete_stl(final):
    d,r,s=final
    check=validate_file(OUT/'stl/temple_v2_complete.stl',expected_bounds=[[0,0,0],[100,72.314,4]],
                        expected_volume=r['expected_prism_volumes_mm3']['assembly'])
    assert check['watertight'] and check['components']==1 and check['degenerate_triangles']==0
    assert r['planar_partition']['valid_partition']
    assert r['planar_partition']['overlap_area_mm2']==pytest.approx(0,abs=1e-6)


@pytest.mark.parametrize('i,name,zlo,zhi',[(1,'black',0,1.6),(2,'blue',1.6,2.4),(3,'red',2.4,3.2),(4,'ivory',3.2,4.)])
def test_v2_actual_color_band(final,i,name,zlo,zhi):
    _,r,_=final
    c=validate_file(OUT/'stl'/f'band_{i}_{name}.stl',expected_volume=r['expected_prism_volumes_mm3'][name],components=None)
    assert c['bounds_mm'][0][2]==pytest.approx(zlo,abs=1e-6)
    assert c['bounds_mm'][1][2]==pytest.approx(zhi,abs=1e-6)


def test_v2_continuous_support_and_cross_sections(final):
    d,r,_=final
    assert not d['magnets']
    for (_,a),(_,b) in zip(list(d['masks'].items()),list(d['masks'].items())[1:]):
        assert b.difference(a).area<1e-5
    assert all(x['symmetric_difference_area_mm2']<.03 for x in r['actual_stl_sections'])
    assert sum(r['expected_prism_volumes_mm3'][n] for n in d['palette'])==pytest.approx(r['assembly']['volume_mm3'],abs=.02)


def test_v2_brush_calligraphy_print_counters(final):
    d,_,_=final
    assert d['text']=='庙隍城' and d['plaque_font'].startswith('Ma Shan Zheng')
    holes=[Polygon(h) for p in polygons(d['masks']['ivory'].intersection(box(37,35,63,46))) for h in p.interiors]
    assert len(holes)==8
    for h in holes:
        x0,y0,x1,y1=h.bounds
        assert min(x1-x0,y1-y0)>=.60


def test_v2_colored_bambu_projects_and_actual_gcode(final):
    _,r,s=final
    expected=r['expected_prism_volumes_mm3']
    assert len(validate_project(OUT/'3mf/chenghuang_temple_v2_P1S_AMS.3mf',expected))==4
    geom,audit,_=native_audit(OUT/'3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf',expected)
    assert len(geom)==4 and audit['total_layers']==20
    assert [x['start_layer_z_mm'] for x in audit['color_changes']]==[1.8,2.6,3.4]
    assert audit['plaque_final_layer_extrusion_coverage_fraction']>.85
    assert s['slicer_result']['return_code']==0
    assert s['slicer_result']['sliced_plates'][0]['filament_change_times']==3
    assert s['slicer_result']['sliced_plates'][0]['warning_message']==''
    assert not s['physical_print_tested']


def test_v2_actual_exports_logs_and_preview_images(final):
    _,_,_=final
    logs=json.loads((OUT/'source/export_log.json').read_text())
    assert len(logs)==6 and all(x['exit_code']==0 and 'ERROR:' not in x['stderr'] for x in logs)
    for name in ['front_four_colors.png','front_effect.png','relief_tilted.png','dimensions_and_layers.png','actual_sliced_paths.png']:
        with Image.open(OUT/'preview'/name) as im:im.verify()
    with zipfile.ZipFile(OUT/'3mf/chenghuang_temple_v2_P1S_AMS_sliced.3mf') as z:
        assert z.testzip() is None
        for name in ['Metadata/plate_1.png','Metadata/plate_1_small.png']:
            assert len(z.read(name))>1000
