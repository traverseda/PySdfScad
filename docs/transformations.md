# Transformations

## From Openscad

### Movement operations

#### Translate

{{scad_image(
"""
translate([-10,-10,5])cube([10,10,10]);
"""
)}}

#### rotate

{{scad_image(
"""
rotate([0,0,45])cube([10,10,10]);
"""
)}}

### CSG operations

Under Hephorge most CSG operations support the "smooth" argument.

#### Difference

{{scad_image(                       
"""                                
difference(){
        cube([10,10,10]);
        translate([12,12,-1])cylinder(r=10,h=12); 
}
"""
)}}

{{scad_image(                       
"""                                
difference(smooth = 1){
        cube([10,10,10]);
        translate([12,12,-1])cylinder(r=10,h=12); 
}
"""
)}}

#### Intersection

{{scad_image(
"""                                
intersection(){
        cube([10,10,10]);                  
        cylinder(r=10,h=12); 
}
"""
)}}

{{scad_image(
"""                                
intersection(smooth=1){
        cube([10,10,10]);                  
        cylinder(r=10,h=12); 
}
"""
)}}


## Hephorge extentions

### Blend

{{scad_image(
"""
blend(ratio=0.5){
	cube([10,10,10]);
	translate([5,5,5])sphere(r=10);
}
"""
)}}

### Shell

Very usefull for making things like pipes or moulds.

{{scad_image(
"""
difference(){
	shell(thickness=1)cube([10,10,10]);
	translate([12,12,-1])cylinder(r=10,h=12);
}
"""
)}}
