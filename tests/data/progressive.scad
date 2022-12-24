// We'll start with a comment

/* and another multiline

comment */

foo= 1+1;
bar = 1+3.14;
echo(bar);
//echo(0.1 + 0.1 + 0.1 - 0.3);
echo([1,2,3]);
echo(1+2, 32, foo=2, bar="biz");

//Interesting to note that you can happily apply
// operators to a function...
union()echo("foo");

union()cylinder(r=2,h=2);
union(){
    foo = 13;
    echo(foo=foo);
    cylinder(h=2,r=2);
    cylinder(h=1,r=3);

}

translate([10,10])cylinder(r=2,h=4);