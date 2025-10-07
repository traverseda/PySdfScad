import sys, os
import textwrap
import pkgutil
import pysdfscad
import sdf
#from pysdfscad.main import EvalOpenscad, openscad_parser
from pysdfscad.main import OpenscadFile, colorize_html
import importlib.resources
from loguru import logger
from pathlib import Path
import os

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QAction, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMenuBar, QMenu,\
        QHBoxLayout, QWidget, QSplitter, QFileDialog, QMessageBox, QFrame,\
        QGridLayout, QTextEdit, QTabWidget
from PySide6.QtCore import Qt, QSettings, QPoint, QSize, QThread, Slot as pyqtSlot, Signal as pyqtSignal, QObject, QBuffer, QIODevice
from PySide6.QtUiTools import QUiLoader

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np


from lark import Lark
import json

from threading import Thread
from pathlib import Path

from collections import defaultdict

logger = logger.opt(ansi=True)

#Try to get pyinstaller to work...
import OpenGL.platform.egl

def themes():
    themeData = importlib.resources.open_binary('pysdfscad_qtgui', 'themes.json').read()
    data = json.loads(themeData)
    out = {}
    for item in data['themes']:
        name = item['name']
        del item['name']
        out[name]=item
    return out

class THEME:
    black=0
    red=1
    green=2
    yellow=3
    blue=4
    purple=5
    cyan=6
    white=7
    brightBlack=8
    brightRed=9
    brightGreen=10
    brightYellow=11
    brightBlue=12
    brightPurple=13
    brightCyan=14
    brightWhite=15
    foreground=16
    background=17
    all_items = ('black','red','green','yellow','blue','purple','cyan','white','brightBlack','brightRed',
                'brightGreen','brightYellow','brightBlue','brightPurple','brightCyan',
                 'brightWhite','foreground','background')




from pathlib import Path

EXAMPLE_TEXT="""
// intersection.scad - Example for intersection() usage in OpenSCAD

echo(version=version());

module example_intersection()
{
	intersection() {
		difference() {
			union(smooth=10) {
				cube([30, 30, 30], center = true);
				translate([0, 0, -25])
					cube([15, 15, 50], center = true);
			}
			union() {
				cube([50, 10, 10], center = true);
				cube([10, 50, 10], center = true);
				cube([10, 10, 50], center = true);
			}
		}
		translate([0, 0, 5])
			cylinder(h = 50, r1 = 20, r2 = 5, center = true);
	}
}

example_intersection();



// Written by Clifford Wolf <clifford@clifford.at> and Marius
// Kintel <marius@kintel.net>
//
// To the extent possible under law, the author(s) have dedicated all
// copyright and related and neighboring rights to this software to the
// public domain worldwide. This software is distributed without any
// warranty.
//
// You should have received a copy of the CC0 Public Domain
// Dedication along with this software.
// If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
"""

from pysdfscad_qtgui.logWidget import QTextEditLogger
from contextlib import redirect_stdout

class LoggerWriter:
    def __init__(self, level):
        # self.level is really like using log.debug(message)
        # at least in my case
        self.level = level

    def write(self, message):
        # if statement reduces the amount of newlines that are
        # printed to the logger
        if message != '\n':
            self.level(message)

    def flush(self):
        pass

import os

log_format='<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'

class MainUi(QMainWindow):
    def __init__(self):
        super().__init__() # Call the inherited classes __init__ method
        loader = QUiLoader()
        ui_file_data = importlib.resources.open_binary('pysdfscad_qtgui', 'main.ui').read()
        ui_buffer = QBuffer()
        ui_buffer.setData(ui_file_data)
        ui_buffer.open(QIODevice.ReadOnly)
        self.ui_window = loader.load(ui_buffer)

        self.setCentralWidget(self.ui_window.centralWidget())
        self.setMenuBar(self.ui_window.menuBar())
        self.setStatusBar(self.ui_window.statusBar())
        self.setWindowTitle(self.ui_window.windowTitle())

        self.sideSplitter = self.findChild(QSplitter, "sideSplitter")
        self.tabWidget = self.findChild(QTabWidget, "tabWidget")
        self.action_New = self.ui_window.findChild(QAction, "action_New")
        self.actionOpen = self.ui_window.findChild(QAction, "actionOpen")
        self.actionSave = self.ui_window.findChild(QAction, "actionSave")
        self.actionSave_As = self.ui_window.findChild(QAction, "actionSave_As")
        self.actionExit = self.ui_window.findChild(QAction, "actionExit")
        self.actionRender = self.ui_window.findChild(QAction, "actionRender")
        self.actionExport_Mesh = self.ui_window.findChild(QAction, "actionExport_Mesh")

        self.readSettings()

        self.openscadFile=OpenscadFile()
        self.mesh=None

        self.preview3d=gl.GLViewWidget(self.sideSplitter)
        self.preview3d.setCameraPosition(distance=40)

        self.logger=QTextEditLogger(self.sideSplitter)
        self._logger_handle_id=logger.add(self.logger, colorize=True,format=log_format)

        self.editor=QTextEdit()
        font = QFont()
        font.setFamily('Consolas')
        font.setFixedPitch(True)
        font.setPointSize(10)
        font.setBold(True)
        self.editor.setFont(font)
        self.editor.setPlainText(EXAMPLE_TEXT)

        self.tabWidget.addTab(self.editor,"Source")

        #self._exampleMenu(self.findChild(QMenu,"menuExamples"))

        self.astPreview=QTextEdit()
        self.astPreview.setReadOnly(True)
        self.tabWidget.addTab(self.astPreview,"AST")

        self.pythonPreview=QTextEdit()
        self.pythonPreview.setReadOnly(True)
        self.tabWidget.addTab(self.pythonPreview,"Python")

        self._connectActions()

    def _connectActions(self):
        # Connect File actions
        self.action_New.triggered.connect(self.newFile)
        self.actionOpen.triggered.connect(self.openFile)
        self.actionSave.triggered.connect(self.saveFile)
        self.actionSave_As.triggered.connect(self.saveFileAs)
        self.actionExit.triggered.connect(self.close)
        self.actionRender.triggered.connect(self.render)
        self.actionExport_Mesh.triggered.connect(self.exportMesh)
        # Connect Edit actions
#        self.copyAction.triggered.connect(self.copyContent)
#        self.pasteAction.triggered.connect(self.pasteContent)
#        self.cutAction.triggered.connect(self.cutContent)
        # Connect Help actions
#        self.helpContentAction.triggered.connect(self.helpContent)
#        self.aboutAction.triggered.connect(self.about)

    def newFile(self):
        self.openscadFile.file=OpenscadFile()
        self.openscadFile.reload()

    def saveFileAs(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
            self.openscadFile.file=Path(filename)
            self.saveFile()
        self.setWindowTitle(f"{self.openscadFile.file} - pySdfScad")


    @logger.catch
    def _render(self):
        try:
            #Try and set background threads to a *low* priority,
            # since people on the internet seem confused about this
            # a higher nice value means your program is *nicer* to
            # other programs, and will get out of their way.
            os.nice(14)
        except: pass

        self.openscadFile.text=self.editor.toPlainText()
        self.astPreview.setPlainText(self.openscadFile.as_ast())
        self.pythonPreview.setPlainText(self.openscadFile.as_python())
        result = list(self.openscadFile.run())
        if not result:
            logger.info("No top level geometry to render")
        else:
            self.result=result[0]
            if isinstance(self.result,sdf.SDF2):
                self.result=self.result.extrude(0.1)
            import numpy as np
            with redirect_stdout(LoggerWriter(logger.opt(depth=1).info)):
                points = self.result.generate()
            points, cells = np.unique(points, axis=0, return_inverse=True)
            cells = cells.reshape((-1, 3))
            self.mesh=(points,cells)
    
            meshdata = gl.MeshData(vertexes=points, faces=cells)
            mesh = gl.GLMeshItem(meshdata=meshdata,
                                 smooth=False, drawFaces=True,
                                 drawEdges=False,
                                 shader="normalColor",
                                 color = (1,1,1,1), edgeColor=(0.2, 0.5, 0.2, 1)
                                 )
            self.preview3d.clear()
            g = gl.GLGridItem()
            g.setSize(200, 200)
            g.setSpacing(10, 10)

            a=gl.GLAxisItem()
            a.setSize(10,10,10)

            self.preview3d.addItem(g)
            self.preview3d.addItem(a)
            self.preview3d.addItem(mesh)

    def exportMesh(self):
        if not self.result:
            return
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilters(["STL file (*.stl)","Guess from extention (*)"])
        dlg.selectNameFilter("STL file (*.stl)")
        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
            self.result.save(filename)

    def openFile(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        dlg.setNameFilters(["Scad files (*.scad)","All files (*)"])
        dlg.selectNameFilter("Scad files (*.scad)")
        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
            self.openscadFile.file=Path(filename)
            self.openscadFile.reload()
            self.editor.setPlainText(self.openscadFile.text)
        self.setWindowTitle(f"{self.openscadFile.file} - pySdfScad")

    def saveFile(self):
        if not self.openscadFile.file:
            self.saveFileAs()
        else:
            self.openscadFile.text=self.editor.toPlainText()
            self.openscadFile.save()

    def render(self):
        self.logger._text=[]
        logger.warning(f"Early \x1b[31malpha!\x1b[0m Really!")
        logger.warning(f'Save your files \x1b[31mregularly\x1b[0m')
        logger.info(f"Started new render with file {self.openscadFile.file}")
        self.preview3d.clear()
        self.astPreview.setPlainText("")
        self.pythonPreview.setPlainText("")
        thread = Thread(target=self._render)
        thread.start()

    def closeEvent(self, event):
        logger.remove(self._logger_handle_id)
        settings = QSettings()
        settings.setValue('geometry',self.saveGeometry())
        settings.setValue('windowState',self.saveState())
        super().closeEvent(event)

    def readSettings(self):
        settings = QSettings()
        try:
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
        except:
            logger.warning("Couldn't restore window state from settings")

    def _loadExample(self,file):
        self.editor.setPlainText(file.read_text())

    def _exampleMenu(self,parent):
        """Generate examples based on folder structure
        """
        #ToDO: this is a bunch of files we need to check for during
        # startup, which will reduce startup time (especially on non-ssds).
        # Can we generate this menu dynamically?
        module_path = Path(os.path.dirname(os.path.realpath(__file__)))

        nested_dict = lambda: defaultdict(nested_dict)
        nest = nested_dict()

        for a in (module_path/"examples").glob("**/*.scad"):
            rel = a.relative_to(module_path/"examples")
            nested=nest
            for b in rel.parent.parts:
                nested=nested[b]
            nested[a.name]=a

        def recursive_menu(item,parent):
            for key, value in item.items():
                if isinstance(value, dict):
                    menu = QMenu(key, parent)
                    for i in recursive_menu(value,menu):
                        menu.addMenu(i)
                    yield menu
                else:
                    text = value.read_text
                    action = parent.addAction(key)
                    action.triggered.connect(lambda: self.editor.setPlainText(text()))

        menu_items=list(recursive_menu(nest,parent))
        parent.addMenu(menu_items[0])


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("pysdfscad")
#    app.setWindowIcon(QtGui.QIcon(str(ui_dir/'logo.png')))
#    win = Window()
    win=MainUi()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
