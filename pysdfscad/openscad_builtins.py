import sdf
from functools import reduce
import inspect
from loguru import logger
import itertools
import lark
import math

def module_echo(*args,**kwargs):
    out = [str(i) for i in args]
    for k,v in kwargs.items():
        out.append(k+"="+str(v))
    logger.opt(depth=1).info("ECHO: "+", ".join(out))
    return
    yield

var_undef = None
var_true = True
var_false = False

def module_children():
    return
    yield

class NewChildContext():
    """Manages child context for openscad operators, by saving the old
    context and restoring it when you exit the context handler.
    """

    def __enter__(self):
        pass
#        global module_children
        print("Enter childcontext",module_children)
#        self.old_children = module_children

    def __exit__(self, exception_type, exception_value, traceback):
        pass
#        global module_children
        print("Exit  childcontext",module_children)
#        module_children = self.old_children

def module_sphere(r):
    yield sdf.sphere(r)

def cylinder(context,r=0,r1=None,r2=None,h=None,center=False):
    if r1 ==None : r1=r
    if r2 == None: r2=r
    if center == False:
        return sdf.capped_cone([0,0,0], sdf.Z*h, r1, r2)
    elif center==True:
        return sdf.capped_cone([0,0,0], sdf.Z*h, r1, r2).translate(-sdf.Z*h/2)


def cube(context,size, center=False):
    x,y,z=size
    offset=(0,0,0)
    if not center:
        offset=[x/2,y/2,z/2]
    return sdf.box(size).translate(offset)

def for_op(context,**kwargs):
    children=[]
    keys = kwargs.keys()
    for item in itertools.product(*kwargs.values()):
        context.vars.update(zip(keys,item))
        children.extend(context.functions['children_list']())
    return children

def module_union(smooth=0):
    children = list(module_children())
    print("module_children",children)
    if not children: return
    yield reduce(lambda a,b: sdf.union(a,b,k=smooth), children)

def blend(context,ratio=0.5):
    children=context.functions['children_list']()
    child1 = children[0]
    child2 = reduce(sdf.union,children[1:])
    return child1.blend(child2,k=ratio)

def shell(context,thickness=10):
    children = union(context)
    return children.shell(thickness)

def twist(context,degrees):
    #Has some significant weirdness that seems to be related to translation.
    return union(context).twist(degrees)

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

def difference(context, smooth=0):
    children=context.functions['children_list']()
    if not children: return
    return reduce(lambda a,b: sdf.difference(a,b,k=smooth), children)

def intersection(context, smooth=0):
    children=context.functions['children_list']()
    if not children: return
    return reduce(lambda a,b: sdf.intersection(a,b,k=smooth), children)

