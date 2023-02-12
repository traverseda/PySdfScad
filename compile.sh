poetry run python -m nuitka --standalone \
        --nofollow-import-to=tkinter \
        --enable-plugin=pyqt5 \
        --include-package-data=astor \
        --include-data-dir=./pysdfscad_qtgui=./pysdfscad_qtgui \
        --include-data-dir=./pysdfscad=./pysdfscad \
        --include-data-dir=./pysdfscad=./pysdfscad \
	--onefile \
        pysdfscad_qtgui/main.py

