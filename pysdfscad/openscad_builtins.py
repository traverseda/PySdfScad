import sdf
from functools import reduce
from loguru import logger
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

def echo(*args,**kwargs):
    out = [str(i) for i in args]
    for k,v in kwargs.items():
        out.append(k+"="+str(v))
    logger.info("ECHO: "+", ".join(out))


sin = math.sin

def cos(context, i): return math.cos(i)
openscad_functions['cos']=cos

def version(context):
    import pkg_resources
    my_version = pkg_resources.get_distribution('pysdfscad').version
    return my_version.split(".")

openscad_functions['version']=version

def sphere(context,r):
    return sdf.sphere(r)

openscad_operators['sphere']=sphere

def cylinder(context,r=0,r1=None,r2=None,h=None,center=False):
    if r1 ==None : r1=r
    if r2 == None: r2=r
    if center == False:
        return sdf.capped_cone([0,0,0], sdf.Z*h, r1, r2)
    elif center==True:
        return sdf.capped_cone([0,0,0], sdf.Z*h, r1, r2).translate(-sdf.Z*h/2)

openscad_operators['cylinder']=cylinder

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

def union(context, smooth=0):
    children=context.functions['children_list']()
    if not children: return
    return reduce(lambda a,b: sdf.union(a,b,k=smooth), children)

openscad_operators['union']=union

def blend(context,ratio=0.5):
    children=context.functions['children_list']()
    child1 = children[0]
    child2 = reduce(sdf.union,children[1:])
    return child1.blend(child2,k=ratio)

openscad_operators['blend']=blend

def shell(context,thickness=10):
    children = union(context)
    return children.shell(thickness)

openscad_operators['shell']=shell

def twist(context,degrees):
    #Has some significant weirdness that seems to be related to translation.
    return union(context).twist(degrees)

#openscad_operators['twist']=twist

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

def difference(context, smooth=0):
    children=context.functions['children_list']()
    if not children: return
    return reduce(lambda a,b: sdf.difference(a,b,k=smooth), children)

openscad_operators['difference']=difference

def intersection(context, smooth=0):
    children=context.functions['children_list']()
    if not children: return
    return reduce(lambda a,b: sdf.intersection(a,b,k=smooth), children)

openscad_operators['intersection']=intersection
