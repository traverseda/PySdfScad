// We'll start with a comment

/* and another multiline

comment */


foo= 1+1;

echo(1);
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