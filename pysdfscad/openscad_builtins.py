import sdf
from functools import reduce
import itertools
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

def sin(context, i): return math.sin(i)
openscad_functions['sin']=sin

def cos(context, i): return math.cos(i)
openscad_functions['cos']=cos

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

def for_op(context,**kwargs):
    children=[]
    keys = kwargs.keys()
    for item in itertools.product(*kwargs.values()):
        context.vars.update(zip(keys,item))
        children.extend(context.functions['children_list']())
    return children

openscad_operators['for']=for_op

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

def difference(context):
    children=context.functions['children_list']()
    if not children: return
    return reduce(sdf.difference, children)

openscad_operators['difference']=difference

def intersection(context):
    children=context.functions['children_list']()
    if not children: return
    return reduce(sdf.intersection, children)

openscad_operators['intersection']=intersection
