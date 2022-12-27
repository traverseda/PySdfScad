// We'll start with a comment

/* and another multiline

comment */

foo= 1+1;
bar = 1+3.14;
echo(bar);
//echo(0.1 + 0.1 + 0.1 - 0.3);
echo([1,2,3]);
echo([]);
echo(1+2, 32, foo=2, bar="biz");

//Interesting to note that you can happily apply
// operators to a function...
union()echo("foo");
sphere(r=20);

cube([20,20,50],center=true);

union()sphere(r=2);
union(){
    foo = 13;
    echo(foo=foo);
    sphere(r=2);
    sphere(r=3);
}

translate([40,40])sphere(r=10);

function func1(r)=r;

function func0(r1,r2,foo="bar") = r1+r2;
echo(func0(1,2));

module doublesphere(r){
    sphere(r);
    translate([r,0])sphere(r);
}

doublesphere(12){};