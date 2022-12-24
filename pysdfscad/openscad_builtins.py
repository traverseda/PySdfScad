import sdf
from functools import reduce
import lark

openscad_functions={}
openscad_operators={}
openscad_vars={}

def echo(context,*args,**kwargs):
    out = [str(i) for i in args]
    for k,v in kwargs.items():
        out.append(k+"="+str(v))
    print("ECHO: "+", ".join(out))
    return None

def cylinder(context,r,h):
    return sdf.capped_cylinder(0, h, r)

openscad_functions['echo']=echo
openscad_functions['cylinder']=cylinder

def union(context):
    children=context.functions['children_list']()
    if not children: return lark.visitors.Discard
    return reduce(lambda x, y: sdf.union(x,y), children)

openscad_operators['union']=union

def translate(context,vector):
    if len(vector)==2:
        x,y = vector
        z=0
    elif len(vector)==3:
        x,y,z=vector
    else:
        raise TypeError(f"Unable to convert translate({vector}) parameter to a vec3 or vec2 of numbers")
    return union(context).translate((x,y,z))

openscad_operators['translate']=translate
