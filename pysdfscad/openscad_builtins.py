import sdf
from functools import reduce
import lark
import math

openscad_functions={}
openscad_operators={}
openscad_vars={
    "true": True,
    "false": False,
    "PI": math.pi,
    'undef': None,
}

def echo(context,*args,**kwargs):
    out = [str(i) for i in args]
    for k,v in kwargs.items():
        out.append(k+"="+str(v))
    context.logger.info("ECHO: "+", ".join(out))
    return args, kwargs

openscad_functions['echo']=echo
openscad_operators['echo']=echo

def sphere(context,r):
    return sdf.sphere(r)

openscad_operators['sphere']=sphere

def cube(context,size, center=False):
    x,y,z=size
    offset=(0,0,0)
    if not center:
        offset=[x/2,y/2,z/2]
    return sdf.box(size).translate(offset)

openscad_operators['cube']=cube

def union(context):
    children=context.functions['children_list']()
    if not children: return
    return reduce(sdf.union, children)

openscad_operators['union']=union

def translate(context,vector):
    if len(vector)==2:
        x,y = vector
        z=0
    elif len(vector)==3:
        x,y,z=vector
    else:
        raise TypeError(f"Unable to convert translate({vector}) parameter to a vec3 or vec2 of numbers")
    children = union(context)
    if not children: return
    return children.translate((x,y,z))

openscad_operators['translate']=translate
