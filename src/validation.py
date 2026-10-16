"""Fail on invalid geometry; never repair or replace geometry silently."""
from pathlib import Path
import numpy as np
import trimesh


def validate_mesh(mesh, expected_bounds=None, expected_volume=None, components=1):
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError('No triangle geometry')
    if not np.isfinite(mesh.vertices).all():
        raise ValueError('Nonfinite vertices')
    if np.any(mesh.area_faces <= 1e-10):
        raise ValueError('Degenerate triangle')
    canonical = np.sort(mesh.faces, axis=1)
    if len(np.unique(canonical, axis=0)) != len(mesh.faces):
        raise ValueError('Duplicate triangle')
    if not mesh.is_watertight:
        raise ValueError('Mesh is not watertight')
    if not mesh.is_winding_consistent or not mesh.is_volume or mesh.volume <= 0:
        raise ValueError('Invalid solid or orientation')
    count = len(mesh.split(only_watertight=False))
    if components is not None and count != components:
        raise ValueError(f'Expected {components} solid(s), got {count}')
    if expected_bounds is not None and not np.allclose(mesh.bounds, expected_bounds, atol=1e-4, rtol=0):
        raise ValueError(f'Wrong bounds: {mesh.bounds}')
    if expected_volume is not None and not np.isclose(mesh.volume, expected_volume, atol=1e-3, rtol=1e-6):
        raise ValueError(f'Wrong volume: {mesh.volume}, expected {expected_volume}')
    return dict(bounds_mm=mesh.bounds.tolist(), size_mm=mesh.extents.tolist(),
                volume_mm3=float(mesh.volume), triangles=len(mesh.faces),
                watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
                degenerate_triangles=int(np.count_nonzero(mesh.area_faces <= 1e-10)),
                components=count)


def validate_file(path, **kwargs):
    # process=False avoids hiding broken geometry; merging STL triangle vertices is
    # necessary for connectivity, but no faces are removed and no holes are filled.
    path = Path(path)
    mesh = trimesh.load(path, force='mesh', process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f'No mesh in {path}')
    mesh.merge_vertices()
    return validate_mesh(mesh, **kwargs)
