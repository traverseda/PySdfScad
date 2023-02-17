from lark import Lark
from loguru import logger
import pathlib, sys
from pathlib import Path
from pysdfscad.compiler import OpenscadToPy
import numpy as np
import astor

#We can get general language definitions here: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/The_OpenSCAD_Language#Chapter_1_--_General
# I try to stick to the same terminology as the book, but it's really not a
# direct 1 to 1 translation. For example I can't really have objects that aren't fundamentally function calls,
# which is why I'd have to go out of my way to keep you from storing an object in a variable.

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalTrueColorFormatter

import pysdfscad.openscad_builtins

def colorize_ansi(source):
    from pygments import highlight
    import pygments.lexers.python #Required or nuitka won't find it
    import pygments.formatters.terminal256
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalTrueColorFormatter
    return highlight(source, PythonLexer(), TerminalTrueColorFormatter())

def colorize_html(source):
    from pygments import highlight
    from pygments.lexers import PythonLexer
    import pygments.formatters.html
    from pygments.formatters import HtmlFormatter
    return highlight(source, PythonLexer(), HtmlFormatter())

class OpenscadFile():
    def __init__(self,file=None):
        self.text=""
        self.file=file
        self.compiled=None
        self.reload()

    def reload(self):
        if self.file:
            self.text=self.file.read_text()
        else:
            self.text=""
        return self

    def save(self):
        self.file.write_text(self.text)
        return self

    def ast(self):
        parser = Lark.open("openscad.lark", rel_to=__file__, propagate_positions=True)
        tree = parser.parse(self.text)
        return OpenscadToPy().transform(tree)

    def run(self):
        """Compile and run the file, returning a
        generator with top level SDF objects.
        """
        scad_locals = {}
        exec(
            compile(
                self.ast(),
                filename=str(self.file),
                mode="exec",
            ),
            scad_locals,
        )
        return list(scad_locals['main']())

    def as_image(self):
        from PyQt5 import QtWidgets, QtCore, QtGui, QtOpenGL
        import pyqtgraph.opengl as gl
        import pyqtgraph as pg

        app = QtWidgets.QApplication([])

        #Horrible hack to reset the shared opengl context

        viewport = gl.GLViewWidget()        
        viewport.setCameraPosition(distance=40)

        result = list(self.run())[0]

        points = result.generate()
        points, cells = np.unique(points, axis=0, return_inverse=True)
        cells = cells.reshape((-1, 3))
    
        meshdata = gl.MeshData(vertexes=points, faces=cells)
        mesh = gl.GLMeshItem(meshdata=meshdata,
                             smooth=False, drawFaces=True,
                             drawEdges=False,
                             shader="normalColor",
                             color = (1,1,1,1), edgeColor=(0.2, 0.5, 0.2, 1)
                             )

        g = gl.GLGridItem()
        g.setSize(200, 200)
        g.setSpacing(10, 10) 

        a=gl.GLAxisItem()                      
        a.setSize(10,10,10)

        viewport.addItem(a)
        viewport.addItem(g)
        viewport.addItem(mesh)
        viewport.show()

        imageData = viewport.renderToArray((1000, 1000))
        image = pg.makeQImage(imageData).transformed(QtGui.QTransform().rotate(90))

        return image 

    def as_ast(self):
        return astor.dump_tree(self.ast())
    def as_python(self):
        return astor.to_source(self.ast(), add_line_information=True)



openscad_parser = Lark((pathlib.Path(__file__).parent/"openscad.lark").read_text(), propagate_positions=True)

def main():
    f = Path(sys.argv[1])
    interpreter = OpenscadFile(f)
    print(colorize_ansi(interpreter.as_ast()))
    print(colorize_ansi(interpreter.as_python()))
    result = list(interpreter.run())
    if not result:
        logger.info("No top level geometry to render")
    else:
        result[0].save('test.stl')

if __name__ == '__main__':
    main()

