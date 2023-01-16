import logging
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor
import shlex
import re
import html

class QTextEditLogger(QTextEdit,logging.Handler):

    _update_signal=pyqtSignal()

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setFontFamily("monospace")
        self.setReadOnly(True)
        self._text=[]
        self.update_in_place=False
        self._update_signal.connect(lambda:self.update())
        self.update()

    def emit(self, record):
        msg = self.format(record)
        #Check to see if there's a carriege return in the output, if there is we simply
        # overwrite the last line.
        # Won't work for more advanced carriege return hackery, but if you just want to make a simple
        # progress bar it's good enough.
        if "\r" in msg:
            if not self.update_in_place:
                self.update_in_place=True
                self._text.append("")
            self._text[-1]=msg.rstrip()
        else:
            self.update_in_place=False
            self._text.append(msg)
        self._update_signal.emit()

    @pyqtSlot(object)
    def update(self):
        #ToDO, ideally we wouldn't re-render the entire thing every time
        # poor performance for the scroll bars
        text = self._text
        text = (html.escape(i) for i in text)
        text = (replace_ansi(i) for i in text)
        #text = (repr(i.encode("utf-8")) for i in text)
        text = (f"<div>{i}</div>" for i in text)
        self.setHtml("<pre>"+"\n".join(text)+"</pre>")
        #Scroll widget to bottom
        self.verticalScrollBar().setValue(
                    self.verticalScrollBar().maximum())


ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

def replace_ansi(text):
    text = text.replace("\x1b[0m","</span>")
    text = text.replace("\x1b[1m",'<span style="font-weight: bold;">')
    text = text.replace("\x1b[3m",'<span style="font-style: italic;">')
    text = text.replace("\x1b[8m",'<span style="text-decoration: line-through;">')
    text = text.replace("\x1b[4m",'<span style="text-decoration: underline;">')
    text = text.replace("\x1b[30m",'<span style="color:black;">')
    text = text.replace("\x1b[31m",'<span style="color:red;">')
    text = text.replace("\x1b[31m",'<span style="color:red;">')
    text = text.replace("\x1b[32m",'<span style="color:green;">')
    text = text.replace("\x1b[33m",'<span style="color:DarkGoldenRod;">')
    text = text.replace("\x1b[34m",'<span style="color:blue;">')
    text = text.replace("\x1b[35m",'<span style="color:magenta;">')
    text = text.replace("\x1b[36m",'<span style="color:CornflowerBlue;">')#I can't deal with cyan on a white background
    text = text.replace("\x1b[37m",'<span style="color:silver;">')
    return text
    return ansi_escape.sub('', text)
