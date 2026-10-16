#!/usr/bin/env python3
"""Report local capabilities without dumping environment variables or secrets."""
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import subprocess

packages = ['numpy','trimesh','Pillow','opencv-python-headless','shapely',
            'svgpathtools','scipy','matplotlib','pytest','networkx']
if __name__ == '__main__':
    result = dict(os=platform.platform(), python=platform.python_version(),
                  openscad=shutil.which('openscad'),
                  packages={p: importlib.metadata.version(p) for p in packages})
    result['chinese_font_present'] = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc').is_file()
    if result['openscad']:
        run = subprocess.run(['openscad','--version'],capture_output=True,text=True,check=True)
        result['openscad_version'] = (run.stdout+run.stderr).strip()
    print(json.dumps(result,indent=2))
