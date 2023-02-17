import multiprocessing
from pathlib import Path
import hashlib

#Need to run this in a subprocess because of https://github.com/pyqtgraph/pyqtgraph/issues/2618
def scad_image_subprocess(path, code_block):
    from pysdfscad.main import OpenscadFile

    file = OpenscadFile()
    file.text=code_block
    image = file.as_image()
    image.save(str(path))


def define_env(env):

    @env.macro
    def scad_image(code_block):
        manager = multiprocessing.Manager()
        digest = hashlib.md5(code_block.encode()).hexdigest()

        imageRoot = Path('docs/images/auto')
        imageRoot.mkdir(parents=True, exist_ok=True)
        imagePath = imageRoot/(digest+".png")

        if not imagePath.exists():
            p = multiprocessing.Process(target=scad_image_subprocess, args=(imagePath, code_block))
            p.start()
            p.join()
        return '```openscad'+code_block+'```\n\n'+f"![Preview of code block](/images/auto/{digest}.png)\n\n"
