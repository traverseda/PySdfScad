import sys, os
import textwrap
import pkgutil
import pysdfscad
#from pysdfscad.main import EvalOpenscad, openscad_parser
from pysdfscad.main import OpenscadFile, colorize_html
from loguru import logger
from pathlib import Path

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.Qt import QColor, QApplication, QFont, QFontMetrics
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QMenuBar, QMenu,\
        QAction, QHBoxLayout, QWidget, QSplitter, QFileDialog, QShortcut, QMessageBox, QFrame,\
        QGridLayout, QTextEdit
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings, QPoint, QSize, QThread, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QKeySequence
from PyQt5 import QtCore

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np

from PyQt5 import Qsci
from PyQt5.Qsci import QsciScintilla
from PyQt5.Qsci import QsciLexerCustom
from pyqtconsole.console import PythonConsole

from lark import Lark
import json

from threading import Thread
from pathlib import Path

from collections import defaultdict

logger = logger.opt(ansi=True)

def themes():
    data = json.load(open(os.path.dirname(os.path.realpath(__file__))+"/themes.json","r"))
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


class LexerOpenscad(QsciLexerCustom):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.create_parser()
        self.create_styles()

    def create_styles(self):
        theme = themes()['BelafonteDay']
        self.theme={}
        for idx, name in enumerate(THEME.all_items):
            color = theme[name].lstrip('#')
            rgb = QColor(*(int(color[i:i+2], 16) for i in (0, 2, 4)))
            self.theme[name]=rgb
            self.setColor(rgb, idx)
            self.setFont(self.parent().font(), idx)


        self.token_styles = {
                "NAME": THEME.blue,
                "SEMICOLON": THEME.brightPurple,
                "COMMENT": THEME.cyan,
                "ESCAPED_STRING": THEME.yellow,
                "NUMBER": THEME.yellow,
                "LPAR": THEME.red,
                "RPAR": THEME.red,
                "LBRACE": THEME.red,
                "RBRACE": THEME.brightRed,
        }

    def create_parser(self):
        grammar = pkgutil.get_data("pysdfscad","openscad.lark").decode("utf-8")
        #self.lark = Lark(grammar, parser=None, lexer='basic')
        self.lark = Lark(grammar, parser='earley', lexer='dynamic_complete')
        # All tokens: print([t.name for t in self.lark.parser.lexer.tokens])

#    def defaultPaper(self, style):
#        return QColor(39, 40, 34)

    def language(self):
        return "OpenScad"

    def description(self, style):
        return {v: k for k, v in self.token_styles.items()}.get(style, "")

    def styleText(self, start, end):

        self.startStyling(start)
        text = self.parent().bytes(start,end)
        text = bytes(text).decode("utf-8").replace('\x00', '')
        last_pos = 0

        try:
            for token in self.lark.lex(text):
                ws_len = token.start_pos - last_pos
                if ws_len:
                    self.setStyling(ws_len, 0)    # whitespace

                token_len = len(bytearray(token, "utf-8"))
                self.setStyling(
                    token_len, self.token_styles.get(token.type, 0))

                last_pos = token.start_pos + token_len
        except Exception as e:
            print(e)


class EditorAll(QsciScintilla):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set font defaults
        font = QFont()
        font.setFamily('Consolas')
        font.setFixedPitch(True)
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)

        # Set margin defaults
        fontmetrics = QFontMetrics(font)
        self.setMarginsFont(font)
        self.setMarginWidth(0, fontmetrics.width("000") + 6)
        self.setMarginLineNumbers(0, True)
        #self.setMarginsForegroundColor(QColor(128, 128, 128))
        #self.setMarginsBackgroundColor(QColor(39, 40, 34))
        self.setMarginType(1, self.SymbolMargin)
        self.setMarginWidth(1, 12)

        # Set indentation defaults
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setBackspaceUnindents(True)
        #self.setAutoIndent(True)

        self.setIndentationGuides(True)
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, True)
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPASTE, 1)
        self.SendScintilla(
            QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, True)

        lexer = LexerOpenscad(self)
        self.setLexer(lexer)


from pathlib import Path

EXAMPLE_TEXT="""
// intersection.scad - Example for intersection() usage in OpenSCAD

echo(version=version());

module example_intersection()
{
	intersection() {
		difference() {
			union() {
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

ui_dir=Path(__file__).parent

log_format='<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'

class MainUi(QMainWindow):
    def __init__(self):
        super().__init__() # Call the inherited classes __init__ method
        uic.loadUi( ui_dir/'main.ui', self) # Load the .ui file
        self.readSettings()

        self.openscadFile=OpenscadFile()
        self.mesh=None

        self.preview3d=gl.GLViewWidget(self.sideSplitter)
        self.preview3d.setCameraPosition(distance=40)

        self.logger=QTextEditLogger(self.sideSplitter)
        self._logger_handle_id=logger.add(self.logger, colorize=True,format=log_format)

        self.editor=EditorAll()
        self.editor.setText(EXAMPLE_TEXT)

        self.tabWidget.addTab(self.editor,"Source")

        self._exampleMenu(self.findChild(QMenu,"menuExamples"))

        self.astPreview=QsciScintilla()
        self.astPreview.setIndentationGuides(True)
        self.astPreview.setIndentationsUseTabs(False)
        self.astPreview.setIndentationWidth(4)
        self.astPreview.setLexer(Qsci.QsciLexerPython(self.astPreview))
        self.astPreview.setReadOnly(True)
        self.astPreview.update_in_place=False
        self.tabWidget.addTab(self.astPreview,"AST")

        self.pythonPreview=QsciScintilla()
        self.pythonPreview.setIndentationGuides(True)
        self.pythonPreview.setIndentationsUseTabs(False)
        self.pythonPreview.setIndentationWidth(4)
        self.pythonPreview.setLexer(Qsci.QsciLexerPython(self.pythonPreview))
        self.pythonPreview.setReadOnly(True)
        self.pythonPreview.update_in_place=False
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
        self.openscadFile.text=self.editor.text()
        result = list(self.openscadFile.run())
        if not result:
            logger.info("No top level geometry to render")
        else:
            self.result=result[0]
            import numpy as np
            with redirect_stdout(LoggerWriter(logger.opt(depth=1).info)):
                points = self.result.generate()
            points, cells = np.unique(points, axis=0, return_inverse=True)
            cells = cells.reshape((-1, 3))
            self.mesh=(points,cells)
    
            meshdata = gl.MeshData(vertexes=points, faces=cells)
            mesh = gl.GLMeshItem(meshdata=meshdata,
                                 smooth=False, drawFaces=True,
                                 shader='normalColor',
                                 drawEdges=False, color = (0.2,0.8,0.2,1), edgeColor=(0.2, 0.5, 0.2, 1)
                                 )
            self.preview3d.clear()
            g = gl.GLGridItem()

            g.setSize(200, 200)
            g.setSpacing(10, 10)
            self.preview3d.addItem(g)
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
            self.editor.setText(self.openscadFile.text)
        self.setWindowTitle(f"{self.openscadFile.file} - pySdfScad")

    def saveFile(self):
        if not self.openscadFile.file:
            self.saveFileAs()
        else:
            self.openscadFile.text=self.editor.text()
            self.openscadFile.save()

    def render(self):
        self.logger._text=[]
        logger.warning(f"Early \x1b[31malpha!\x1b[0m Really!")
        logger.warning(f'Save your files \x1b[31mregularly\x1b[0m')
        logger.info(f"Started new render with file {self.openscadFile.file}")
        thread = Thread(target=self._render)
        thread.start()
        self.astPreview.setText(self.openscadFile.as_ast())
        self.pythonPreview.setText(self.openscadFile.as_python())

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
        self.editor.setText(file.read_text())

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
                    action.triggered.connect(lambda: self.editor.setText(text()))

        menu_items=list(recursive_menu(nest,parent))
        parent.addMenu(menu_items[0])


def main():
    app = QApplication(sys.argv)
#    win = Window()
    win=MainUi()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
