"""Test cases based on 3D models stored in data/test_geom.

When adding a new test case you must manually invoke this file
to get it to generate new geometry.

`poetry run python tests/test_geometry.py` or the like.

The intended way to use this is to manually verify the results
every time you add a new test case, make sure the meshes look
like what you're expecting. There's no good way to verify that
a translate *actually* translates anything.

This is a bit brittle, but currently we don't really have a
good solution. If fogleman's SDF library gets the ability to
import geometry and check geometry volume there are some fun
hacks we can do that would let us compare the output directly
to openscad generated meshes.

"""

import inspect, sys, os
import warnings
from test_interpretor import eval_scad
import tempfile
from pathlib import Path
import hashlib

dir_path = os.path.dirname(os.path.realpath(__file__))

def geometry_testcase(func):
    def wrapped(*args,test=True,**kwargs):
        out = func(*args,**kwargs)
        if test==True:
            tmp = tempfile.NamedTemporaryFile(suffix=".stl")
            out.save(tmp.name)
            out_hash = file_digest(tmp)
            #Hash the file
            outpath = Path(dir_path)/"data"/"test_geom"/(func.__name__.removeprefix("test_")+".stl")
            assert outpath.exists()
            file_hash = file_digest(outpath.open("rb"))
            assert out_hash == file_hash
            return
        return out
    return wrapped

@geometry_testcase
def test_sphere():
    geom = eval_scad("sphere(r=20);")
    return geom

def file_digest(file):
    file_hash = hashlib.md5()
    while chunk := file.read(8192):
        file_hash.update(chunk)
    return file_hash.digest()


def main():
    """Generate models for test cases...
    """
    fset = ( out for out in inspect.getmembers(sys.modules[__name__]) if inspect.isfunction(out[1]))
    fset = {name:obj for name,obj in fset if name.startswith("test_")}
    for name, func in fset.items():
        outgeom = func(test=False)
        outpath = Path(dir_path)/"data"/"test_geom"/(name.removeprefix("test_")+".stl")
        orig_hash = file_digest(outpath.open("rb"))
        outgeom.save(str(outpath))
        new_hash = file_digest(outpath.open("rb"))
        if new_hash != orig_hash:
            warnings.warn("New file at `{outpath} has different hash, old:{old_hash} new:{new_hash}`")

if __name__ == "__main__":
    main()
