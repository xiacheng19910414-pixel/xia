#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.validation import validate_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate a real solid STL in mm; fails with nonzero exit code.')
    parser.add_argument('stl',type=Path)
    parser.add_argument('--size',nargs=3,type=float,metavar=('X','Y','Z'))
    parser.add_argument('--volume',type=float)
    args = parser.parse_args()
    report = validate_file(args.stl,expected_volume=args.volume)
    if args.size:
        import numpy as np
        if not np.allclose(report['size_mm'],args.size,atol=1e-4,rtol=0):
            raise ValueError(f"Unexpected size: {report['size_mm']}")
    print(json.dumps(report,indent=2))
