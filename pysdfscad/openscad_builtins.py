import sdf
from functools import reduce, wraps
import inspect
from loguru import logger
import itertools
import lark
import math
from sympy import S,N
import numpy as np

def module_echo(*args,**kwargs):
    def inner(children=lambda:()):
        out = [repr(i) for i in args]
        for k,v in kwargs.items():
            k=k.removeprefix("var_")
            out.append(k+"="+repr(v))
        logger.opt(depth=1).info("ECHO: "+", ".join(out))
        return
        yield
    return inner

def function_version():
    from importlib.metadata import version
    return version('pysdfscad')

var_undef = None
var_true = True
var_false = False

class Range:
    """Generator that works like an openscad range
    """
    def __init__(self,start,stop,step):
        self.start=float(start)
        self.stop=float(stop)
        self.step=float(step)
        
    def __iter__(self):
        count = 0
        while True:
            temp = float(self.start + self.count * self.step)
            if self.step > 0 and temp >= self.stop:
                break
            elif self.step < 0 and temp <= self.stop:
                break
            yield temp
            count += 1

    def __repr__(self):
        return f"[{self.start}:{self.step}:{self.stop}]"

def scad_range(start,stop,step):
    return Range(start,stop,step)


#def function_S(i):
#    """Convert the given string into a symbolic representation.
#    """
#    return S(i)

#def function_N(i):
#    """Convert a sympy object into a float
#    """
#    return N(i)

def module_sphere(var_r):
    def inner(children=lambda:()):
        yield sdf.sphere(var_r)
    return inner

def module_cylinder(var_r=0, var_r1=None, var_r2=None, var_h=None, var_center=False):

    if var_r1 == None : var_r1=var_r
    if var_r2 == None : var_r2=var_r

    def inner(children=lambda:()):
        if var_center == False:
            yield sdf.capped_cone([0,0,0], sdf.Z*var_h, var_r1, var_r2)
        elif var_center==True:
            yield sdf.capped_cone([0,0,0], sdf.Z*var_h, var_r1, var_r2).translate(-sdf.Z*var_h/2)
    return inner


def module_cube(var_size, var_center=False):
    def inner(children=lambda:()):
        x,y,z=var_size
        offset=(0,0,0)
        if not var_center:
            offset=[x/2,y/2,z/2]
        yield sdf.box(var_size).translate(offset)
    return inner

def module_union(var_smooth=1):
    def inner(children=lambda:()):
        children = list(children())
        if not children: return
        yield reduce(lambda a,b: sdf.union(a,b,k=var_smooth), children)
    return inner

def module_intersection(var_smooth=0):
    def inner(children=lambda:()):
        children = list(children())
        if not children: return
        yield reduce(lambda a,b: sdf.intersection(a,b,k=var_smooth), children)
    return inner

def module_difference(var_smooth=0):
    def inner(children=lambda:()):
        children = list(children())
        if not children: return
        yield reduce(lambda a,b: sdf.difference(a,b,k=var_smooth), children)
    return inner

def blend(context,ratio=0.5):
    children=context.functions['children_list']()
    child1 = children[0]
    child2 = reduce(sdf.union,children[1:])
    return child1.blend(child2,k=ratio)

def module_shell(context,thickness=10):
    def inner(children=lambda:()):
        children = list(module_union()children())[0]
        return children.shell(thickness)
    return inner

def twist(context,degrees):
    #Has some significant weirdness that seems to be related to translation.
    return union(context).twist(degrees)

def module_translate(vector):
    def inner(children=lambda:()):
        if len(vector)==2:
            x,y = vector
            z=0
        elif len(vector)==3:
            x,y,z=vector
        else:
            raise TypeError(f"Unable to convert translate({vector}) parameter to a vec3 or vec2 of numbers")
        children = list(module_union()(children))[0]
        if not children: return
        yield children.translate((x,y,z))
    return inner



