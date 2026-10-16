// Units: mm. Default total bounds: [0,0,0] .. [100,70,3].
width = 100;
height = 70;
base_thickness = 2;
decor_height = 1;
margin = 4;
gap = 2;
part = "assembly"; // assembly, base, red, yellow, green, blue
part_width = (width - 2*margin - gap)/2;
part_height = (height - 2*margin - gap)/2;
assert(width > 2*margin+gap && height > 2*margin+gap);
assert(base_thickness > 0 && decor_height > 0 && margin > 0 && gap > 0);
assert(part == "assembly" || part == "base" || part == "red" ||
       part == "yellow" || part == "green" || part == "blue");
module base() { color("royalblue") cube([width,height,base_thickness]); }
module tile(col, ix, iy) {
    color(col) translate([margin+ix*(part_width+gap),
                         margin+iy*(part_height+gap),base_thickness])
        cube([part_width,part_height,decor_height]);
}
module selected() {
    if (part == "assembly" || part == "base") base();
    if (part == "assembly" || part == "red") tile("red",0,1);
    if (part == "assembly" || part == "yellow") tile("gold",1,1);
    if (part == "assembly" || part == "green") tile("limegreen",0,0);
    if (part == "assembly" || part == "blue") tile("royalblue",1,0);
}
// A real CSG union removes internal contact faces in the overall printable STL.
union() { selected(); }
