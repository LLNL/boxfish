
import sys
#from OpenGL.GLUT import glutInit
from MainWindow import *


def run():
    """This method runs the boxfish application."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # May be called on some systems, not on others and the latter
    # will crash without it if GLUT stuff is used.
    #glutInit(sys.argv)

    app = QApplication(sys.argv)
    #app.setStyle('plastique')
    bf = MainWindow()

    # Open runs based on command line arguments
    if len(sys.argv) > 1:
        bf.openRun(*sys.argv[1:])

    bf.show()
    bf.raise_()
    sys.exit(app.exec_())
