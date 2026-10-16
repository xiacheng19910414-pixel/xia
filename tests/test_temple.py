"""Validate the real final architectural STL/3MF deliverables, not mock exports.

Run scripts/build_temple.py before this suite if artifacts are absent. A source
hash check prevents old files from being accepted after editing the design.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pytest
from shapely import Polygon, Point
from shapely.affinity import scale
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.temple_design import design,PALETTE,Z_BANDS
from scripts.build_temple import geometry_checks,polygons

OUT=ROOT/'output'/'chenghuang_temple'

@pytest.fixture(scope='module')
def temple():
    assert (OUT/'validation.json').exists(), 'Generate actual temple exports first'
    metadata=json.loads((OUT/'design.json').read_text())
    assert metadata['design_source_sha256']==hashlib.sha256((ROOT/'src'/'temple_design.py').read_bytes()).hexdigest(), 'Stale geometry: rebuild temple'
    assert metadata['mesh_source_sha256']==hashlib.sha256((ROOT/'src'/'terrace_mesh.py').read_bytes()).hexdigest(), 'Stale construction mesh: rebuild temple'
    d=design()
    return d,geometry_checks(d,OUT)


def test_temple_actual_exports_and_solids(temple):
    d,r=temple
    assert r['with_slots']['watertight'] and r['no_slots']['watertight']
    assert r['with_slots']['components']==r['no_slots']['components']==1
    assert np.allclose(r['with_slots']['size_mm'],[100,d['height'],4],atol=1e-4)
    assert 72<=d['height']<=75
    assert r['planar_partition']['valid_partition']
    assert abs(r['planar_partition']['overlap_area_mm2'])<1e-6
    for result in [r['with_slots'],r['no_slots'],r['geometry_3mf'],*r['bands'].values(),*r['colored_3mf'].values(),r['coupon']]:
        assert result['degenerate_triangles']==0
        assert result['winding_consistent'] and result['volume_mm3']>0


def test_temple_four_nested_print_bands(temple):
    d,r=temple
    assert list(Z_BANDS.values())==[(0,1.6),(1.6,2.4),(2.4,3.2),(3.2,4)]
    assert len(PALETTE)==4 and len(set(PALETTE.values()))==4
    assert [round(z/.2) for _,z in Z_BANDS.values()]==[8,12,16,20]
    for item in r['nested_support']:
        assert item['unsupported_area_mm2']<1e-5
    assert sum(v['volume_mm3'] for v in r['bands'].values())==pytest.approx(r['with_slots']['volume_mm3'],rel=1e-5)
    # Some bands intentionally have disconnected islands; all are supported in
    # the assembled print. They are not standalone pieces for glue assembly.
    assert r['bands']['blue']['components']>1
    assert all(item['symmetric_difference_area_mm2']<.03 for item in r['actual_stl_sections'])


def test_temple_outline_proportions_and_symmetry(temple):
    d,_=temple
    a=d['masks']['black']
    assert a.geom_type=='Polygon' and a.is_valid and len(a.interiors)==0
    assert a.area/(100*d['height'])<.75 # Not a rectangular photographic background.
    other=scale(a,xfact=-1,yfact=1,origin=(50,0))
    assert a.symmetric_difference(other).area<.05
    for g in d['masks'].values():
        assert g.is_valid
        for p in polygons(g):
            assert p.area>.05
            assert all(Polygon(h).area>=.05 for h in p.interiors)


def test_temple_magnet_clearances_and_actual_cavities(temple):
    d,r=temple
    assert len(d['magnets'])==2
    left,right=d['magnets']
    assert left['x']+right['x']==pytest.approx(100,abs=.001)
    assert left['y']==right['y']
    for m in d['magnets']:
        assert m['diameter']==8.2 and m['depth']==2.2
        assert 4-m['depth']>=1.2
        assert d['masks']['ivory'].covers(Point(m['x'],m['y']).buffer(4.1+1.2))
    assert r['no_slots']['volume_mm3']>r['with_slots']['volume_mm3']
    assert r['coupon']['size_mm']==[50,20,4]


def test_temple_upright_text_and_printable_counters(temple):
    d,_=temple
    assert d['text']=='庙隍城'
    letters=d['letters']
    assert len(letters)==3
    assert letters[0].bounds[2]<letters[1].bounds[0]<letters[2].bounds[0]
    for letter in letters:
        assert letter.is_valid
        for p in polygons(letter):
            for ring in p.interiors:
                x0,y0,x1,y1=Polygon(ring).bounds
                assert min(x1-x0,y1-y0)>=.60


def test_temple_real_openscad_logs_and_previews(temple):
    logs=json.loads((OUT/'source'/'export_log.txt').read_text())
    assert len(logs)==8
    assert all(x['exit_code']==0 and 'ERROR:' not in x['stderr'] for x in logs)
    for filename in ['front_four_colors.png','dimensions_and_layers.png','front_effect.png','relief_tilted.png']:
        with Image.open(OUT/'preview'/filename) as im:im.verify()
    with Image.open(OUT/'preview'/'front_four_colors.png') as im:
        pixels=np.array(im.convert('RGB'))
        for value in PALETTE.values():
            rgb=list(bytes.fromhex(value[1:]))
            assert np.count_nonzero(np.all(pixels==rgb,axis=-1))>1000
    for filename in ['front_effect.png','relief_tilted.png']:
        with Image.open(OUT/'preview'/filename) as im:
            colors=im.convert('RGB').getcolors(im.width*im.height)
            assert im.width>=1000 and len(colors)>4


def test_temple_actual_size_pdf(temple):
    import re
    d,_=temple
    data=(OUT/'preview'/'front_actual_size.pdf').read_bytes()
    match=re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)',data)
    assert match
    assert float(match[1])*25.4/72==pytest.approx(100,abs=.001)
    assert float(match[2])*25.4/72==pytest.approx(d['height'],abs=.001)
