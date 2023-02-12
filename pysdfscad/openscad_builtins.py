import sdf #type: ignore
from functools import reduce, wraps
import inspect
from loguru import logger #type: ignore
import itertools
import lark
import math
import numpy as np
from appdirs import AppDirs
from pathlib import Path
from urllib.request import urlopen
import urllib.parse
from zipfile import ZipFile
import typing

dirs = AppDirs("pySdfScad", "pySdfScad")

Geometry = typing.Iterator[sdf.SDF3|sdf.SDF2]

def child(func=lambda: tuple()):
    def indexer(idx=None):
        def inner(module_children):
            if not idx:
                yield from func()
            elif isinstance(idx,int):
                yield list(func())[idx]
            else:
                result = list(func())
                for i in idx:
                    yield result[i]
        return inner
    return indexer

no_children = child()

def module_children():
    def inner(children=no_children):
        yield from children()
    return inner

def module_echo(*args,**kwargs):
    def inner(children):
        out = [repr(i) for i in args]
        for k,v in kwargs.items():
            k=k.removeprefix("var_")
            out.append(k+"="+repr(v))
        logger.opt(depth=1).info("ECHO: "+", ".join(out))
        yield from children()(no_children)
    return inner

def div(left,right):
    """Openscad compatible division, returns inf
    on division by zero.
    """
    if right == 0: return float("inf")
    return left/right

def function_version():
    from importlib.metadata import version
    return version('pysdfscad')

def function_str(*args):
    args = (str(i) for i in args)
    return "".join(args)

def function_cos(a):
    return math.cos(a)

def function_sin(a):
    return math.sin(a)

def function_atan2(left,right):
    return math.atan2(left,right)

def function_min(*a):
    return min(*a)

def function_max(*a):
    return max(*a)

def function_sqrt(a):
    return math.sqrt(a)

def function_pow(left,right):
    return math.pow(left,right)

var_undef = None
var_true = True
var_false = False
var_PI = math.pi

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
            temp = float(self.start + count * self.step)
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
    def inner(children):
        yield sdf.sphere(var_r)
    return inner

def module_circle(var_r,var_fn=None):
    def inner(children):
        yield sdf.circle(var_r)
    return inner

def module_square(var_size,var_center=False):
    def inner(children=no_children):
        x,y=var_size
        offset=(0,0)
        if not var_center:
            offset=[x/2,y/2]
        yield sdf.rectangle(var_size).translate(offset)
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

def module_linear_extrude(var_height=1,var_center=True, var_convexity=None,var_twist=0):
    def inner(children=lambda:()):
        children = list(module_union()(children))[0]
        yield children.extrude(var_height)
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
    def inner(children):
        children = list(children()(no_children))
        if not children: return
        yield reduce(lambda a,b: sdf.union(a,b,k=var_smooth), children)
    return inner

def module_intersection(var_smooth=0):
    def inner(children):
        children = list(children()(no_children))
        if not children: return
        yield reduce(lambda a,b: sdf.intersection(a,b,k=var_smooth), children)
    return inner

def module_difference(var_smooth=0):
    def inner(children):
        children = list(children()(no_children))
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
        children = list(module_union()(children()))[0]
        return children.shell(thickness)
    return inner

def twist(context,degrees):
    #Has some significant weirdness that seems to be related to translation.
    return union(context).twist(degrees)

def module_rotate(vector):
    def inner(children):
        if isinstance(vector,(int,float)):
            x=0
            y=0
            z=vector
        elif len(vector)==1:
            x=vector[0]
            y=0
            z=0
        elif len(vector)==2:
            x,y = vector
            z=0
        elif len(vector)==3:
            x,y,z=vector
        else:
            raise TypeError(f"Unable to convert translate({vector}) parameter to a vec3 or vec2 of numbers")
        children = list(module_union()(children))[0]
        if not children: return

        #Convert degrees to radians
        x,y,z = (i*(math.pi/180) for i in (x,y,z))
        #ToDo, these are not degrees
        if isinstance(children,sdf.SDF3):
            yield children.rotate(x,sdf.X).rotate(y,sdf.Y).rotate(z,sdf.Z)
        elif isinstance(children,sdf.SDF2):
            yield children.rotate(z)
        else:
            raise TypeError(f"{type(children)} not expected")
    return inner

def module_translate(vector):
    def inner(children):
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

def module_extrude(height):
    def inner(children=lambda:()):
        children = list(module_union()(children))[0]
        if not children: return
        yield children.extrude((height))
    return inner


def module_text(var_text,var_size=10,var_font="Arimo",var_width=None,var_height=None):
    #ToDo: https://stackoverflow.com/questions/43060479/how-to-get-the-font-pixel-height-using-pils-imagefont-class
    #Set up halign and valign
    if not var_height: var_height=var_size

    fontparts = var_font.split("-")
    if len(fontparts)==2:
        family, varient = fontparts
    elif len(fontparts)==1:
        family=fontparts[0]
        varient="Regular"
    else:
        raise Exception(f"Can't handle font {var_font}, too many hyphens in name")


    fontpath = Path(dirs.user_cache_dir)/"fonts"
    fontpath.mkdir(parents=True, exist_ok=True)

    name_stripped=family.replace(" ","")
    font_file = fontpath/f"{name_stripped}-{varient}.ttf"
    print(font_file)
    if not font_file.exists():
        fonturl = "https://fonts.google.com/download?family="+urllib.parse.quote(family)
        logger.opt(depth=1).debug(f"Downloading font family from {fonturl}")
        with urlopen(fonturl) as zipresp:
            with ZipFile(BytesIO(zipresp.read())) as theZip:
                fileNames = theZip.namelist()
                for fileName in fileNames:
                    if fileName.endswith('ttf'):
                        content = theZip.open(fileName).read()
                        (fontpath/Path(fileName).name).write_bytes(content)
    else:
        logger.opt(depth=1).debug(f"Found {name_stripped}-{varient}.ttf in font cache")

    def text_inner(children=lambda:()):
        w, h = sdf.measure_text(str(font_file), var_text,height=var_size,width=var_width)
        yield sdf.text(str(font_file), var_text, height=var_height,width=var_width,).translate((w/2,h/2))

    return text_inner

