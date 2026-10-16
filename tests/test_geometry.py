from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_sample import build, read_3mf
from src.validation import validate_mesh

@pytest.fixture(scope='module')
def rendered(tmp_path_factory):
    out = tmp_path_factory.mktemp('openscad')
    return out,build(out)


def test_actual_openscad_exports(rendered):
    out,report = rendered
    assert len(report['parts']) == 6
    assert len(report['commands']) == 7
    assert np.allclose(report['parts']['assembly']['size_mm'],[100,70,3])
    assert report['parts']['assembly']['volume_mm3'] == pytest.approx(19400)
    assert (out/'magnet.scad').is_file()
    for part,result in report['parts'].items():
        assert result['watertight'] and result['winding_consistent']
        assert result['degenerate_triangles'] == 0
        assert result['components'] == 1
        assert result['volume_mm3'] > 0


def test_parts_fill_overall_volume(rendered):
    _,report = rendered
    volumes = report['parts']
    assert sum(v['volume_mm3'] for k,v in volumes.items() if k!='assembly') == pytest.approx(volumes['assembly']['volume_mm3'])
    boxes = [np.array(volumes[k]['bounds_mm']) for k in ('red','yellow','green','blue')]
    for i,a in enumerate(boxes):
        assert a[0,2] == 2 and a[1,2] == 3
        for b in boxes[i+1:]:
            assert np.any(np.minimum(a[1],b[1])-np.maximum(a[0],b[0]) <= 0)


def test_real_3mf_and_png(rendered):
    out,_ = rendered
    validate_mesh(read_3mf(out/'3mf'/'assembly.3mf'),
                  expected_bounds=[[0,0,0],[100,70,3]],expected_volume=19400)
    from PIL import Image
    with Image.open(out/'preview'/'magnet.png') as im:
        im.verify()
    with Image.open(out/'preview'/'magnet.png') as im:
        assert im.width >= 1000 and im.height >= 700
        pixels = np.array(im.convert('RGB'))
        for rgb in ([255,0,0],[255,215,0],[50,205,50],[65,105,225]):
            assert np.count_nonzero(np.all(pixels == rgb,axis=-1)) > 1000


def test_nondefault_dimensions(tmp_path):
    report = build(tmp_path,width=80,height=60,base=3,decor=2,extra=False)
    assert np.allclose(report['parts']['assembly']['size_mm'],[80,60,5])
    assert report['parts']['assembly']['volume_mm3'] == pytest.approx(21400)


@pytest.mark.parametrize('bad', ['hole','degenerate','duplicate','inverted','empty','sheet','nonfinite'])
def test_reject_broken_geometry(bad):
    mesh = trimesh.creation.box(extents=[10,10,2])
    if bad == 'hole':
        mesh.update_faces(np.arange(len(mesh.faces)-1))
    elif bad == 'degenerate':
        mesh.faces = np.vstack([mesh.faces,[0,0,1]])
    elif bad == 'duplicate':
        mesh.faces = np.vstack([mesh.faces,mesh.faces[0]])
    elif bad == 'inverted':
        mesh.invert()
    elif bad == 'empty':
        mesh = trimesh.Trimesh()
    elif bad == 'sheet':
        mesh.vertices[:,2] = 0
    elif bad == 'nonfinite':
        mesh.vertices[0,0] = np.nan
    with pytest.raises(ValueError):
        validate_mesh(mesh)


def test_wrong_dimensions_and_volume_fail():
    mesh = trimesh.creation.box(extents=[10,10,2])
    with pytest.raises(ValueError,match='Wrong bounds'):
        validate_mesh(mesh,expected_bounds=[[0,0,0],[100,70,3]])
    with pytest.raises(ValueError,match='Wrong volume'):
        validate_mesh(mesh,expected_volume=1)


def test_disconnected_solids_fail():
    a = trimesh.creation.box()
    b = a.copy()
    b.apply_translation([3,0,0])
    with pytest.raises(ValueError,match='solid'):
        validate_mesh(trimesh.util.concatenate([a,b]))


@pytest.mark.parametrize('values', [{'width':10},{'decor':0},{'base':-1},{'height':float('nan')}])
def test_invalid_parameters_fail(tmp_path,values):
    with pytest.raises(ValueError):
        build(tmp_path,**values)
