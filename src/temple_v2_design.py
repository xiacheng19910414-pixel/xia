"""V2 FRONT DESIGN STUDY, not yet a printable model.

Reference-coordinate reconstruction of the supplied 1536 x 1152 image.
Primary coordinates follow the pictured eaves/columns; no camera perspective.
All reference pixels are mapped by ONE uniform mm scale, never stretched.
"""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.mplconfig'))
import numpy as np
from shapely import Polygon, Point, LineString, box, union_all, set_precision
from shapely.affinity import scale, translate, affine_transform
from svgpathtools import parse_path

PALETTE={'black':'#202329','blue':'#24355C','red':'#AF302B','ivory':'#EAE0C9'}
PIXEL_MM=100/1376


def U(*g):return union_all([p for p in g if not p.is_empty])
def D(x,y,r):return Point(x,y).buffer(r,quad_segs=16)
def S(points,w=12):return LineString(points).buffer(w/2,cap_style='round',join_style='round',quad_segs=8)
def R(x0,y0,x1,y1,r=3):return box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=8)
def P(d):
    path=parse_path(d);pts=[]
    for seg in path:
        pts.extend((seg.point(t).real,seg.point(t).imag) for t in np.linspace(0,1,max(2,int(seg.length()/3)),endpoint=False))
    return Polygon(pts)
def C(d,w=12):
    path=parse_path(d);pts=[]
    for seg in path:
        pts.extend((seg.point(t).real,seg.point(t).imag) for t in np.linspace(0,1,max(2,int(seg.length()/3)),endpoint=False))
    end=path[-1].end;pts.append((end.real,end.imag))
    return S(pts,w)
def M(g):return scale(g,xfact=-1,yfact=1,origin=(768,0))
def pair(g):return U(g,M(g))


def plaque_letters():
    """True brush-calligraphy glyphs, preserving font proportions and baseline."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    font_path=Path(__file__).resolve().parents[1]/'assets/fonts/mashanzheng/MaShanZheng-Regular.ttf'
    if not font_path.is_file():raise RuntimeError('Missing vendored Ma Shan Zheng font')
    font=FontProperties(fname=str(font_path))
    outlines=[]
    for char in '庙隍城':
        t=TextPath((0,0),char,size=10,prop=font)
        g=Polygon()
        for contour in t.to_polygons():
            ring=Polygon(contour)
            if not ring.is_valid:raise ValueError(f'Invalid font contour for {char}')
            g=g.symmetric_difference(ring)
        outlines.append(g)
    ymin=min(g.bounds[1] for g in outlines)
    ymax=max(g.bounds[3] for g in outlines)
    f=93/(ymax-ymin)
    glyphs=[]
    # One scale and a shared baseline: do not distort each calligraphic glyph
    # separately to fit a rectangle. Y is flipped only to the reference canvas.
    for g in outlines:
        g=affine_transform(g,[f,0,0,-f,0,ymax*f]).buffer(1.0,join_style='round')
        glyphs.append(g)
    cursor=0
    arranged=[]
    for g in glyphs:
        arranged.append(translate(g,xoff=cursor-g.bounds[0]))
        cursor+=g.bounds[2]-g.bounds[0]+11
    group=U(*arranged)
    x0,y0,x1,y1=group.bounds
    return translate(group,xoff=768-(x0+x1)/2,yoff=570-(y0+y1)/2)


def bracket(cx,y,w=46):
    # Flared dou-gong arms + stepped central bearing, rather than a U icon.
    f=w/46
    points=[(-23,0),(-15,0),(-9,12),(0,18),(9,12),(15,0),(23,0),
            (16,22),(6,27),(6,40),(-6,40),(-6,27),(-16,22)]
    arms=Polygon([(cx+x*f,y+dy*f) for x,dy in points])
    return U(arms,R(cx-11*f,y+43*f,cx+11*f,y+55*f,2))


def design_v2():
    # Original high central roof: flat central ridge and restrained corner curves.
    roof=P('M362 160 C352 159 351 181 362 199 L362 235 C374 313 423 373 498 410 L536 427 L1000 427 L1038 410 C1113 373 1162 313 1174 235 L1174 199 C1185 181 1184 159 1174 160 L1163 168 C1169 186 1150 201 1121 209 C1076 225 1026 224 977 205 C837 215 699 215 559 205 C510 224 460 225 415 209 C386 201 367 186 373 168 Z')
    wing=P('M90 371 Q80 369 80 385 Q80 399 93 411 L84 430 C96 486 135 543 219 585 L268 611 L520 644 L554 583 L555 438 L320 410 C290 406 269 395 273 377 L262 368 C248 374 251 392 261 403 L281 417 C207 437 135 424 105 398 L107 381 Z')
    # Roof-wheel and cloud-scroll decorations sit directly on the ridge.
    crest=U(P('M475 200 C468 184 477 174 477 158 L472 148 L485 151 L489 137 L500 142 L505 129 L516 139 L527 132 L534 147 L549 145 L545 158 C559 176 551 193 538 202 Q511 216 475 200 Z'),C('M532 193 C549 218 566 211 578 202 C590 196 579 180 568 187 Q560 194 571 197',29))
    finial=U(D(768,177,14),R(757,189,779,215,4))
    base=P('M138 1128 L1398 1128 L1398 1103 L1373 1062 L1300 1039 L236 1039 L163 1062 L138 1103 Z')
    bodies=U(R(525,399,1011,1062,4),pair(R(276,585,575,1065,4)))
    a=U(roof,pair(wing),pair(crest),finial,base,bodies)
    # Round the physical tip ends; keep silhouette derived from architecture.
    a=a.buffer(-5.5,join_style='round').buffer(5.5,join_style='round')
    B=[];RED=[];W=[];CUT=[]
    main_plane=P('M369 198 C414 235 489 243 559 219 C699 229 837 229 977 219 C1047 243 1122 235 1167 198 L1169 224 C1112 264 1060 285 1014 287 L522 287 C476 285 422 264 367 224 Z')
    B.extend([main_plane,C('M368 191 C415 226 484 236 558 212 Q768 223 978 212 C1052 236 1121 226 1168 191',12)])
    fascia=P('M374 271 Q430 299 516 307 L1020 307 Q1106 299 1162 271 L1156 300 Q1098 328 1020 334 L516 334 Q438 328 380 300 Z')
    RED.append(fascia)
    # Limited tile count; repeated tile ends form a proper eave rhythm.
    for i,x in enumerate(np.linspace(515,1021,15)):
        topx=x+(768-x)*.08
        B.append(D(x,286,11.5))
        RED.append(S([(topx,242),(x-5,273)],12))
        if i in [1,4,7,10,13]:W.append(D(x,286,6))
    # Curved side tiles follow the reference's side roof edges, not huge bowls.
    for x,y,tx,ty in [(431,256,465,235),(464,269,491,239)]:
        B.append(pair(D(x,y,11)))
        RED.append(pair(S([(tx,ty),(x+5,y-12)],12)))
    side_plane=P('M94 408 C146 446 234 450 308 426 L539 440 L534 494 L491 505 C308 522 149 505 99 457 Z')
    B.extend([pair(side_plane),pair(C('M95 400 C146 438 235 440 308 418 L539 431',12))])
    side_edge=parse_path('M108 459 C205 511 384 525 527 496')
    for i,t in enumerate(np.linspace(.02,.98,13)):
        p=side_edge.point(t)
        B.append(pair(D(p.real,p.imag,11.5)))
        top_y=447 if p.real<300 else 444+(p.real-300)*.017
        RED.append(pair(S([(p.real+20,top_y+10),(p.real+3,p.imag-14)],12)))
        if i in [1,4,8,11]:W.append(pair(D(p.real,p.imag,6)))
    RED.append(pair(P('M109 484 C212 545 394 550 540 516 L535 549 C408 591 220 583 128 524 Z')))
    # Ridge scrolls: continuous silhouette, no ball-on-a-stick decoration.
    crest_ink=U(D(511,167,22).difference(D(511,167,10)),
                C('M486 197 Q493 205 516 203 Q539 204 550 214',12),
                C('M546 181 C556 167 578 172 579 184 C579 194 564 197 562 188',12))
    B.extend([pair(crest_ink),D(768,177,7)])
    # Two-storey central corbel rhythm; stone columns frame it.
    for i,cx in enumerate(np.linspace(568,968,8)):
        B.append(bracket(cx,350,48))
        B.append(bracket(cx,406,37))
        if i in [1,3,4,6]:W.append(R(cx-8,375,cx+8,386,2))
    for cx in np.linspace(219,488,7):
        B.append(pair(bracket(cx,573,40)))
    # Fine but broad friezes with large lozenges rather than zigzag strips.
    B.append(R(586,454,950,493,4))
    W.extend([R(590,454,946,466,2),R(590,482,946,494,2)])
    for cx in np.linspace(618,918,9):
        W.append(Polygon([(cx-8,474),(cx,465),(cx+8,474),(cx,483)]))
    side_frieze=R(319,681,520,735,3)
    B.append(pair(side_frieze))
    W.append(pair(U(R(324,685,515,697,2),R(324,720,515,732,2))))
    for cx in [346,393,440,487]:
        lozenge=Polygon([(cx-11,708),(cx,697),(cx+11,708),(cx,719)])
        W.append(pair(lozenge))
    # Full-height stone posts, shaped bases, and red timber posts.
    W.extend([pair(R(526,421,574,1032,5)),pair(R(276,617,321,1027,5)),
              pair(R(515,401,583,432,5)),pair(R(264,608,333,637,5))])
    scroll_base=P('M276 854 L307 854 L307 1018 L325 1045 L231 1045 L236 1006 Q220 991 235 969 Q225 948 243 932 Q237 910 252 892 L255 873 Z')
    W.append(pair(scroll_base))
    CUT.append(pair(C('M268 887 C249 906 259 916 267 920 C249 937 248 950 260 961 C240 976 247 992 260 998',12)))
    RED.extend([pair(R(581,638,616,1027,4)),pair(R(324,744,347,1027,3)),pair(R(495,744,520,1027,3)),
                pair(R(353,758,490,960,4))])
    # Large door inset panels, coarse lattice and lower raised panels.
    B.append(pair(R(368,779,409,879,3)))
    CUT.append(pair(R(374,785,407,870,4)))
    RED.append(pair(R(363,890,480,907,3)))
    B.append(pair(R(372,921,409,954,3)))
    # Central lintel, double doors and two separate suspended lanterns.
    B.append(R(629,712,907,735,4))
    RED.append(R(627,740,909,755,3))
    for cx in np.linspace(643,893,10):B.append(D(cx,719,9))
    RED.extend([R(686,763,760,958,3),R(776,763,850,958,3),
                R(674,752,686,966,3),R(850,752,862,966,3),R(675,873,861,886,2)])
    for x in [704,735,794,825]:CUT.append(R(x,783,x+12,868,3))
    B.extend([R(698,902,748,944,3),R(788,902,838,944,3)])
    for cx in [650,886]:
        lantern=scale(D(cx,799,22),xfact=1,yfact=.8,origin=(cx,799))
        RED.extend([lantern,R(cx-6,760,cx+6,780,2),R(cx-9,816,cx+9,828,2),R(cx-6,829,cx+6,850,2)])
        CUT.append(R(cx-6,787,cx+6,809,3))
    # Curved sparrow braces under the central and side plaques.
    brace=P('M578 635 L676 635 Q668 659 641 677 Q619 690 593 693 L593 679 Q622 672 635 652 L578 652 Z')
    W.append(pair(brace))
    side_brace=P('M323 746 L386 746 C376 766 353 781 326 784 L326 770 Q349 764 356 757 L323 757 Z')
    local_mirror=scale(side_brace,xfact=-1,yfact=1,origin=(420,0))
    W.extend([pair(side_brace),pair(local_mirror)])
    # Smaller sign with proper frame and actual, upright Chinese text.
    plaque=R(600,505,936,635,6)
    B.append(plaque)
    frame=R(600,505,936,635,6).difference(R(612,517,924,623,3))
    RED.append(frame)
    text=plaque_letters();W.append(text)
    # Traditional side-profile guardian lion: nose, mane, chest, bent haunch,
    # front paw and scroll tail. No round smiling face or anthropomorphic arms.
    lion=P('M484 933 C483 906 486 881 496 866 C487 854 490 841 499 833 C491 826 495 815 507 811 C511 801 526 803 534 810 C549 806 560 816 558 827 Q569 827 571 839 Q572 850 560 858 L552 860 C552 869 552 880 546 890 L552 925 L561 933 L561 944 L524 944 L519 924 L513 944 L478 944 L478 934 Z')
    lion=U(lion,C('M495 908 C469 907 469 889 480 884 Q487 880 487 889',13))
    W.append(pair(lion))
    lion_cuts=U(D(547,828,6),C('M566 838 L565 847 L553 856',11),
                C('M514 823 C497 830 499 846 511 851',11),
                C('M534 898 L531 925',12),S([(541,934),(553,934)],11))
    lion_halo=pair(lion.buffer(11,join_style='round').difference(lion)).intersection(box(0,0,1536,935))
    CUT.extend([pair(lion_cuts),lion_halo])
    # Elegant, correctly sized stone pedestals. No oversized square magnet pods.
    W.extend([pair(R(470,944,576,960,3)),pair(R(480,968,567,1037,4)),pair(R(473,1040,574,1055,3))])
    CUT.append(pair(R(494,980,553,1025,3)))
    # Solid tablet emblem on each plinth, >= 0.8 mm features.
    emblem=U(Polygon([(523,984),(543,1003),(523,1022),(503,1003)]))
    W.append(pair(emblem))
    # Three clear stairs; black recesses remain visible between them.
    W.extend([R(224,1046,1312,1062,2),R(190,1078,1346,1094,2),R(166,1110,1370,1127,2)])
    # Process cut-outs before the priority masks; clear space around facial marks.
    cut=U(*CUT)
    w=U(*W).difference(cut).intersection(a)
    # The plinth emblem sits above the recessed border (still one ivory height).
    w=U(w,pair(emblem)).intersection(a)
    red=U(*RED).difference(cut).difference(w).intersection(a)
    blue=U(*B).difference(cut).difference(U(w,red)).intersection(a)
    # One similarity transform: geometric front-view reference -> actual mm.
    x0,y0,x1,y1=a.bounds
    factor=100/(x1-x0)
    def mm(g):return set_precision(affine_transform(g,[factor,0,0,-factor,-x0*factor,y1*factor]),.001)
    def area_only(g):
        # Boolean boundary coincidences can leave zero-area lines/points;
        # they are not decorative features and must never become geometry.
        if g.geom_type=='Polygon':return g if g.area>.02 else Polygon()
        if hasattr(g,'geoms'):return U(*[area_only(p) for p in g.geoms])
        return Polygon()
    a,b,r,w=[area_only(mm(g)) for g in [a,blue,red,w]]
    masks={'black':a,'blue':U(b,r,w),'red':U(r,w),'ivory':w}
    visible={'black':area_only(a.difference(masks['blue'])),'blue':b,'red':r,'ivory':w}
    return dict(masks=masks,visible=visible,width=a.bounds[2]-a.bounds[0],height=a.bounds[3]-a.bounds[1],
        palette=PALETTE,reference_scale_mm_per_pixel=factor,
        status='FRONT DESIGN STUDY ONLY; not a printable STL or validated 3D model',
        planned_total_thickness_mm=4.0,planned_layer_height_mm=.2,
        planned_z_bands_mm={'black':[0,1.6],'blue':[1.6,2.4],'red':[2.4,3.2],'ivory':[3.2,4.0]},
        text='庙隍城',text_layout_height_mm=95*factor,
        plaque_font='Ma Shan Zheng / 马善政毛笔楷书',
        plaque_font_license='SIL Open Font License 1.1; unmodified font included in assets/fonts/mashanzheng',
        magnet_strategy='No slots in this revision: keep reference-proportioned lion plinths; use rear adhesive magnetic sheet. Reassess cavity roof thickness after design review.',
        nominal_major_stroke_mm=12*factor,
        remaining_checks=['Chinese glyph minimum stroke and counter widths at final size',
            'Individual ornamental minimum widths and clearances',
            'Final 3D manifold export, magnet decisions, slicing and physical print'])
