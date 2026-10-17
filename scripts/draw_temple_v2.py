#!/usr/bin/env python3
"""Draw the reference-led V2 front design for review, without claiming a final STL."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.temple_v2_design import design_v2,PALETTE
from scripts.build_temple import plot_geometry,polygons,save_svg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=ROOT/'output'/'chenghuang_temple_v2'


def detail_and_comparison(d):
    # Render from vector geometry rather than editing or retouching images.
    fig,ax=plt.subplots(figsize=(9,3.7))
    for i,(name,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[name],i+1)
    ax.set(xlim=(36.5,63.5),ylim=(35.1,46.0));ax.set_aspect('equal');ax.axis('off')
    fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
    fig.savefig(OUT/'plaque_font_detail.png',dpi=200,facecolor='white');plt.close(fig)
    from src.temple_design import design,PALETTE as old_palette
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    old=design()
    fig,axes=plt.subplots(1,2,figsize=(16,7.6))
    for ax,model,colors,title in [(axes[0],old,old_palette,'旧版'),(axes[1],d,PALETTE,'新版 V2 · 毛笔楷书匾额')]:
        for i,(name,g) in enumerate(model['masks'].items()):plot_geometry(ax,g,colors[name],i+1)
        ax.set(xlim=(-2,102),ylim=(-2,78));ax.set_aspect('equal');ax.axis('off')
        ax.set_title(title,fontproperties=font,fontsize=16,pad=10)
    fig.tight_layout();fig.savefig(OUT/'comparison_v1_v2.png',dpi=180,facecolor='white');plt.close(fig)


def main():
    d=design_v2();OUT.mkdir(parents=True,exist_ok=True)
    assert abs(d['width']-100)<.002
    assert 72<=d['height']<=75
    assert all(g.is_valid for g in d['masks'].values())
    for (n,g),(m,h) in zip(list(d['masks'].items()),list(d['masks'].items())[1:]):
        assert h.difference(g).area<.001, (n,m,h.difference(g).area)
    fig=plt.figure(figsize=(12,9.2));ax=fig.add_axes([0,0,1,1])
    for i,(name,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[name],i+1)
    ax.set(xlim=(-3,103),ylim=(-3,d['height']+3));ax.set_aspect('equal');ax.axis('off')
    fig.savefig(OUT/'front_design_v2.png',dpi=200,facecolor='white')
    save_svg(fig,OUT/'front_design_v2.svg',transparent=True)
    plt.close(fig)
    fig=plt.figure(figsize=(100/25.4,d['height']/25.4));ax=fig.add_axes([0,0,1,1])
    for i,(name,g) in enumerate(d['masks'].items()):plot_geometry(ax,g,PALETTE[name],i+1)
    ax.set(xlim=(0,100),ylim=(0,d['height']));ax.set_aspect('equal');ax.axis('off')
    fig.savefig(OUT/'front_actual_size_v2.pdf',metadata={'Title':'V2 design study / 100 mm width / NOT a validated printable model'})
    plt.close(fig)
    # Actual-mm editable SVG, not a screenshot or photographic texture.
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="{d["height"]}mm" viewBox="0 0 100 {d["height"]}">',
        f'<g transform="translate(0 {d["height"]}) scale(1 -1)">']
    for name,g in d['visible'].items():
        for poly in polygons(g):
            path=[]
            for ring in [poly.exterior,*poly.interiors]:
                path.append('M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in ring.coords)+' Z')
            lines.append(f'<path fill="{PALETTE[name]}" fill-rule="evenodd" d="{" ".join(path)}"/>')
    lines.extend(['</g>','</svg>'])
    (OUT/'editable_mm_v2.svg').write_text('\n'.join(lines)+'\n')
    detail_and_comparison(d)
    metadata={k:v for k,v in d.items() if k not in ('masks','visible')}
    (OUT/'design_status.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(metadata,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
