from sdf import *

openscad_builtins={}

def echo(*args,**kwargs):
    out = [str(i) for i in args]
    for k,v in kwargs.items():
        out.append(k+"="+str(v))
    print("ECHO: "+", ".join(out))
    return None

def cylinder(r,h):
    return capped_cylinder(0, h, r)

openscad_builtins['echo']=echo
openscad_builtins['cylinder']=cylinder
        
