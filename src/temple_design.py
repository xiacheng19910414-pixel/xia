"""Editable 2D architectural construction, in mm, based on the user's front reference.

Four FINAL surface masks are converted to nested layer masks, not independent
unsupported colored decorations. Width normalization is isotropic only.
"""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.mplconfig'))
import numpy as np
from shapely import Polygon, Point, LineString, box, union_all, set_precision
from shapely.affinity import scale, translate
from svgpathtools import parse_path

PALETTE = {'black':'#24262B','blue':'#202F60','red':'#B9312D','ivory':'#E9DFC6'}
Z_BANDS = {'black':(0.,1.6),'blue':(1.6,2.4),'red':(2.4,3.2),'ivory':(3.2,4.)}
ROOT = Path(__file__).resolve().parents[1]


def union(*geoms):
    return union_all([g for g in geoms if not g.is_empty],grid_size=.001)


def disk(x,y,r):
    return Point(x,y).buffer(r,quad_segs=12)


def stroke(points,width=1.0):
    return LineString(points).buffer(width/2,cap_style='round',join_style='round',quad_segs=8)


def path_poly(d):
    path = parse_path(d)
    pts=[]
    for seg in path:
        n=max(2,int(seg.length()/.35)+1)
        pts.extend((seg.point(t).real,seg.point(t).imag) for t in np.linspace(0,1,n,endpoint=False))
    return Polygon(pts)


def curve(d,width=1.):
    path=parse_path(d)
    pts=[]
    for seg in path:
        pts.extend((seg.point(t).real,seg.point(t).imag) for t in np.linspace(0,1,max(3,int(seg.length()/.3)),endpoint=False))
    end=path[-1].end
    pts.append((end.real,end.imag))
    return stroke(pts,width)


def mirror(g):
    return scale(g,xfact=-1,yfact=1,origin=(50,0))


def pair(g):
    return union(g,mirror(g))


def rounded_box(x0,y0,x1,y1,r=.25):
    return box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=6)


def glyphs():
    """Real Noto Sans CJK glyphs: left-to-right 庙隍城, no mirror transform.

    Enlarged to 8.6 mm ink height before a 0.13 mm outline expansion. The
    expansion and measured stroke-size report are explicit, not synthetic text.
    """
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    if not font.exists():
        raise RuntimeError('NotoSansCJK-Bold.ttc required for real Chinese glyphs; install fonts-noto-cjk')
    glyph_list=[]
    for char in '庙隍城':
        tp=TextPath((0,0),char,size=10,prop=FontProperties(fname=str(font)))
        geom=Polygon()
        # Nested contours: keep character counters as holes.
        for contour in tp.to_polygons():
            p=Polygon(contour)
            if not p.is_valid:
                raise ValueError(f'Invalid font outline: {char}')
            geom=geom.symmetric_difference(p)
        x0,y0,x1,y1=geom.bounds
        factor=8.6/(y1-y0)
        geom=translate(scale(geom,xfact=factor,yfact=factor,origin=(x0,y0)),xoff=-x0,yoff=-y0)
        geom=geom.buffer(.13,quad_segs=6,join_style='round')
        glyph_list.append(geom)
    widths=[g.bounds[2]-g.bounds[0] for g in glyph_list]
    spacing=.9
    cursor=50-(sum(widths)+2*spacing)/2
    result=[]
    for g,width in zip(glyph_list,widths):
        result.append(translate(g,xoff=cursor-g.bounds[0],yoff=38.9-g.bounds[1]))
        cursor+=width+spacing
    # The dense 皇 component of 隍 needs larger counters than the original
    # typeface supplies. Rebuild only its 白 box with 0.8 mm strokes and
    # 0.6 mm clear counters, retaining the actual 阝/王 and diagonal cap.
    middle=result[1]
    white_box=box(49.4,43.55,53.2,47.15).difference(union(
        box(50.2,44.35,52.4,44.95),box(50.2,45.75,52.4,46.35)))
    emperor=union(white_box,stroke([(50.9,47.0),(51.5,47.6)],.8),
        box(49.1,42.0,53.6,42.8),box(49.1,40.5,53.6,41.3),
        box(48.9,39.0,53.9,39.8),box(51.0,39.3,51.8,42.5))
    middle=union(middle.intersection(box(45,38.8,48.8,48.0)),emperor)
    result[1]=middle
    # Remove the tiny ornamental counter at the top of 城 and expand the
    # remaining narrow font counters to at least 0.62 mm in both axes.
    for i,g in enumerate(result):
        pp=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
        new=[]
        for p in pp:
            holes=[]
            for ring in p.interiors:
                h=Polygon(ring)
                if h.area<.16:continue
                x0,y0,x1,y1=h.bounds
                h=scale(h,xfact=max(1,.62/(x1-x0)),yfact=max(1,.62/(y1-y0)),origin='center')
                holes.append(h)
            new.append(Polygon(p.exterior).difference(union(*holes)))
        result[i]=union(*new)
    return union(*result),result


def design():
    # Primary silhouette: front elevation, no photographic rectangular background.
    central_roof=path_poly('M20.0 69.0 Q19.0 64.1 22 60.1 Q27 53 34 50.7 L66 50.7 Q73 53 78 60.1 Q81 64.1 80 69 L78.7 69 Q78 64.4 73 64.3 Q69 63.8 65.5 65.5 Q50 64.7 34.5 65.5 Q31 63.8 27 64.3 Q22 64.4 21.3 69 Z')
    wing=path_poly('M0 53.1 Q0 50.4 2.2 48.8 Q10 45.2 17.6 48.5 Q19.8 49.6 20.2 52.7 L21.5 52.7 Q21.1 49.5 25.0 48.9 L35.2 48.6 L35.2 41 Q29.5 34.2 18.4 34.2 L13 34.2 Q4 38.2 .8 44.3 Q0 47.4 0 53.1 Z')
    # At the wing tips the outline is rounded inward by 0.25 mm, then all
    # geometry is uniformly normalized to exactly 100 mm wide.
    wing=wing.buffer(-.25,join_style='round').buffer(.25,join_style='round')
    foundation=Polygon([(4,0),(96,0),(96,2),(94.5,4.7),(86,6.4),(14,6.4),(5.5,4.7),(4,2)])
    body=union(box(33,4.5,67,54),pair(box(13,4.5,35,40)),foundation)
    crest=union(disk(32,70.3,2.7),stroke([(33.3,68.4),(34.6,65.3)],1.8),
                stroke([(29.7,69),(28.2,68.4),(27.5,69)],1.3))
    finial=union(disk(50,68.2,1.3),rounded_box(49.3,64.8,50.7,67.5,.25))
    silhouette=union(central_roof,pair(wing),body,pair(crest),finial)
    silhouette=silhouette.buffer(.12,join_style='round').buffer(-.12,join_style='round')
    # Final blue roof surfaces. Broad bands replace the reference's fine tiles.
    main_tiles=path_poly('M21.3 66.8 Q25 61.9 34.7 64.3 Q50 63.6 65.3 64.3 Q75 61.9 78.7 66.8 L77.4 61.5 Q71 57.9 65 57.9 L35 57.9 Q29 57.9 22.6 61.5 Z')
    main_grooves=[]
    for x in np.linspace(26,74,15):
        main_grooves.append(stroke([(x,58.7),(x+(50-x)*.045,63.6)],.8))
    main_tiles=main_tiles.difference(union(*main_grooves))
    main_ridge=curve('M20.7 68 Q23.8 62.8 34.5 65.1 Q50 64.4 65.5 65.1 Q76.2 62.8 79.3 68',1.15)
    wing_tiles=path_poly('M1.2 51.5 Q6 46 17.7 49.5 Q20 50.4 20.5 51.7 L21.2 48.1 L34 47.5 L34 42.7 Q27.8 39.1 20 40 Q9.7 40.6 2 45.3 Z')
    wing_grooves=[stroke([(x,40),(x+1.9,47.9)],.8) for x in np.arange(5,33,3.2)]
    wing_tiles=wing_tiles.difference(union(*wing_grooves))
    wing_ridge=curve('M1 52 Q4.8 46.9 17.8 49.4 Q20.3 50.5 20.6 51.8 M21.4 48.1 L34.2 47.7',1.1)
    blue=[main_tiles,main_ridge,pair(wing_tiles),pair(wing_ridge)]
    crest_blue=union(disk(32,70.3,2.05).difference(disk(32,70.3,.95)),
                     stroke([(33.2,68.5),(34.2,66.3)],1.0),disk(50,68.2,.8))
    blue.append(pair(crest_blue))
    # Structural brackets: 7 central and 5 on each wing; all strokes >=1.0 mm.
    for x in np.linspace(33,67,7):
        blue.append(curve(f'M{x-1.7} 54.9 Q{x} 51 {x+1.7} 54.9',1.05))
        blue.append(rounded_box(x-.55,50.9,x+.55,52.6,.2))
    for x in [8,13,18,23,28]:
        g=curve(f'M{x-1.5} 38.8 Q{x} 35.2 {x+1.5} 38.8',1.05)
        blue.append(pair(g))
    # Blue frieze and enlarged sign field, retaining real readable characters.
    blue.extend([rounded_box(34.3,37.3,65.7,49.4,.45),
                 pair(rounded_box(16.4,28.6,33.5,32.3,.25)),
                 rounded_box(39.4,28.7,60.6,30.7,.25)])
    # Final red: broad fascia, structural posts, door frames/panels, lanterns.
    red=[curve('M22.3 60 Q29 55.9 35.5 56.3 L64.5 56.3 Q71 55.9 77.7 60',1.9),
         pair(curve('M2.4 44.6 Q12.4 38.3 23.4 39.2 Q29.8 39.3 33.8 42.1',1.9)),
         pair(rounded_box(36.8,6.5,39.2,36.5,.3)),
         pair(rounded_box(16.8,6.9,19.0,28.0,.3)),
         pair(rounded_box(30.7,6.9,32.7,28.0,.3)),
         rounded_box(43.8,7.6,56.2,27.0,.35),
         pair(rounded_box(20.2,8.0,29.2,26.4,.4))]
    # Reduce the grilles to 4 coarse vertical gaps and 2 horizontal rails.
    grille=[]
    for x in [45.6,48.0,52.0,54.4]:
        grille.append(rounded_box(x-.4,12.1,x+.4,25.6,.2))
    grille.extend([rounded_box(44.6,10.3,55.4,11.1,.2),
                   rounded_box(49.6,7.5,50.4,27.1,.2)])
    # All black openings are removed from ALL upper materials, never unsupported.
    black_details=list(grille)
    black_details.append(pair(rounded_box(22,13.0,27.3,24.3,.6)))
    # Lanterns sit in black recesses, with thick hanging stems and tassels.
    for x in [41.6,58.4]:
        red.extend([scale(disk(x,24.9,1.4),xfact=1.1,yfact=1.0,origin=(x,24.9)),
                    stroke([(x,27.6),(x,26.3)],.9),stroke([(x,23.6),(x,22.4)],.9)])
    # Red plaque frame only, blue is exposed inside.
    plaque_outer=rounded_box(34.6,37.1,65.4,49.7,.4)
    plaque_inner=rounded_box(35.4,37.9,64.6,48.9,.2)
    red.append(plaque_outer.difference(plaque_inner))
    # Four-color simplified stonework and three clear step bands.
    ivory=[rounded_box(6.4,.8,93.6,2.0,.15),
           rounded_box(9.2,2.8,90.8,4.0,.15),
           rounded_box(14,4.8,86,6.0,.15),
           pair(rounded_box(13.6,7.0,15.2,34.2,.3)),
           pair(rounded_box(32.2,27.3,33.8,54.3,.3)),
           pair(rounded_box(13.6,6.5,16.0,10,.3)),
           pair(rounded_box(31.5,51.0,34.5,54.7,.35))]
    # The pedestals are intentionally enlarged for an 8.2 mm cavity plus >=1.2 wall.
    pedestal=rounded_box(26.5,5.4,37.5,16.4,.35)
    lion=union(pedestal,
               scale(disk(32,19.5,2.9),xfact=1,yfact=1.2,origin=(32,19.5)),
               disk(32,23.7,2.5),disk(30.2,25.0,.9),disk(33.8,25.0,.9),
               disk(29.8,23.5,.9),disk(34.2,23.5,.9),
               curve('M29.8 18.2 C27.8 18.2 27.4 20.4 28.7 21.1 Q29.5 21.6 29.3 20.3',1.1),
               rounded_box(29.6,16,31.0,20.5,.4),rounded_box(33.0,16,34.4,20.5,.4),
               rounded_box(28.4,15.6,35.6,16.7,.3))
    ivory.append(pair(lion))
    lion_marks=union(disk(31.0,24.0,.42),disk(33.0,24.0,.42),
                     stroke([(30.9,22.5),(32,21.9),(33.1,22.5)],.8),
                     stroke([(31.8,23),(32.2,23)],.8),
                     stroke([(32,16.9),(32,19.8)],.85))
    black_details.append(pair(lion_marks))
    text,letter_shapes=glyphs()
    ivory.extend([text,pair(disk(32,70.3,.6)),disk(50,68.2,.55)])
    # Selected bold stone frieze ornament, not fine floral texture.
    ornament=union(stroke([(18,30.4),(20,31.1),(22,30.4),(24,31.1),(26,30.4),(28,31.1),(30,30.4)],.9))
    ivory.append(pair(ornament))
    # Small red corbel blocks are deliberately omitted to preserve readable gaps.
    cut=union(*black_details)
    raw_w=union(*ivory).intersection(silhouette).difference(cut)
    raw_r=union(*red).intersection(silhouette).difference(cut)
    raw_b=union(*blue).intersection(silhouette).difference(cut)
    # Isotropic normalization: NEVER stretch height separately.
    x0,y0,x1,y1=silhouette.bounds
    factor=100/(x1-x0)
    def norm(g):
        return set_precision(scale(translate(g,xoff=-x0,yoff=-y0),xfact=factor,yfact=factor,origin=(0,0)),.001)
    def clean(g):
        # Drop only sub-print-resolution internal voids (<0.05 mm²). Keeping
        # numerical sliver holes makes OpenSCAD's extrusion triangulation fail.
        pp=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
        return union(*[Polygon(p.exterior,[ring for ring in p.interiors if Polygon(ring).area>=.05]) for p in pp if p.area>=.05])
    a=clean(norm(silhouette).simplify(.008,preserve_topology=True))
    a=union(a,mirror(a)) # Preserve exact symmetric 0..100 mm extrema after simplification.
    # Clean each ink ONCE, then build nested masks top-down. Re-simplifying
    # already-nested masks separately creates nearly coincident boundaries and
    # zero-area triangles during CSG. Shared boundaries must remain identical.
    interior=a.buffer(-.6,join_style='round')
    def ink(g):
        return clean(set_precision(clean(norm(g).simplify(.015,preserve_topology=True)).intersection(interior),.001))
    w=ink(raw_w)
    r=clean(union(ink(raw_r),w))
    b=clean(union(ink(raw_b),r))
    # Intersect at full precision: grid-rounded unions can otherwise leave
    # micron-scale protrusions of an upper mask beyond its lower support.
    a,b,r,w=[set_precision(g,0) for g in (a,b,r,w)]
    b=b.intersection(a)
    r=r.intersection(b)
    w=w.intersection(r)
    masks={'black':a,'blue':b,'red':r,'ivory':w}
    visible={'black':a.difference(b),'blue':b.difference(r),'red':r.difference(w),'ivory':w}
    magnets=[dict(x=round((x-x0)*factor,4),y=round((10.9-y0)*factor,4),diameter=8.2,depth=2.2) for x in [32,68]]
    return dict(masks=masks,visible=visible,magnets=magnets,
                width=100.,height=a.bounds[3]-a.bounds[1],scale=factor,
                letters=[norm(g) for g in letter_shapes],
                reference='User supplied Chenghuang temple front elevation; simplified vector reconstruction, not an automatic pixel trace',
                text='庙隍城',reading='Traditional right-to-left 城隍庙; upright, never mirrored')
