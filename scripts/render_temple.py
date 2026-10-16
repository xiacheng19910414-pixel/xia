#!/usr/bin/env python3
"""Orthographic CPU z-buffer rendering of the exported band STLs.

No image-generation model or fabricated geometry. The four actual material
meshes are rendered at their real thickness, without depth exaggeration.
"""
import argparse
from pathlib import Path
import sys
import numpy as np
import trimesh
from PIL import Image, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.temple_design import PALETTE


def render(out,tilt=0.,azimuth=0.,width=1600):
    out=Path(out)
    rx=np.radians(tilt);rz=np.radians(azimuth)
    rotation=np.array([[1,0,0],[0,np.cos(rx),-np.sin(rx)],[0,np.sin(rx),np.cos(rx)]]) @ np.array([[np.cos(rz),-np.sin(rz),0],[np.sin(rz),np.cos(rz),0],[0,0,1]])
    meshes=[]
    for i,(name,color) in enumerate(PALETTE.items()):
        mesh=trimesh.load(out/'stl'/f'band_{i+1}_{name}.stl',force='mesh',process=False)
        triangles=mesh.triangles @ rotation.T
        meshes.append((triangles,tuple(bytes.fromhex(color[1:]))))
    allverts=np.concatenate([t.reshape(-1,3) for t,_ in meshes])
    mn=allverts.min(axis=0);mx=allverts.max(axis=0)
    padding=45
    factor=(width-2*padding)/(mx[0]-mn[0])
    height=int(np.ceil((mx[1]-mn[1])*factor))+2*padding
    depth=np.full((height,width),-np.inf,dtype=float)
    pixels=np.full((height,width,4),[255,255,255,0],dtype=np.uint8)
    for triangles,color in meshes:
        for triangle in triangles:
            # Cull back-facing triangles: all source solids have validated winding.
            if np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0])[2]<=1e-10:
                continue
            screen=triangle.copy()
            screen[:,0]=(triangle[:,0]-mn[0])*factor+padding
            screen[:,1]=(mx[1]-triangle[:,1])*factor+padding
            low=np.maximum(np.floor(screen[:,:2].min(axis=0)).astype(int),0)
            high=np.minimum(np.ceil(screen[:,:2].max(axis=0)).astype(int),[width-1,height-1])
            x0,y0=low;x1,y1=high
            if x1<x0 or y1<y0:continue
            x=np.arange(x0,x1+1)[None,:]+.5
            y=np.arange(y0,y1+1)[:,None]+.5
            a,b,c=screen
            denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator)<1e-12:continue
            u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
            v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
            w=1-u-v
            z=u*a[2]+v*b[2]+w*c[2]
            region=depth[y0:y1+1,x0:x1+1]
            keep=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)&(z>region)
            region[keep]=z[keep]
            pixels[y0:y1+1,x0:x1+1][keep]=[*color,255]
    model=Image.fromarray(pixels)
    shadow=Image.new('RGBA',model.size,(0,0,0,0))
    alpha=Image.fromarray(pixels[:,:,3]).filter(ImageFilter.GaussianBlur(7))
    shadow.putalpha(alpha.point(lambda v:int(v*.18)))
    background=Image.new('RGBA',model.size,'white')
    background.alpha_composite(shadow,(4,9))
    background.alpha_composite(model)
    path=out/'preview'/('front_effect.png' if tilt==0 else 'relief_tilted.png')
    background.convert('RGB').save(path)
    return path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output'/'chenghuang_temple')
    args=parser.parse_args()
    print(render(args.output))
    print(render(args.output,tilt=32,azimuth=-8))
