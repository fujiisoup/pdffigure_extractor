"""
I learned how to use Qt from https://github.com/giaccone/PyDigitizer
"""
import time
import numpy as np
# modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QSpinBox,
    QGroupBox, QPushButton, QFileDialog, QSizePolicy,
    QRadioButton, QInputDialog, QLabel, QDesktopWidget, QScrollArea,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QVBoxLayout)
from PyQt5.QtGui import QBrush, QColor, QImage, QPainter, QPixmap, QPen
from PyQt5.QtCore import Qt, QObject, QEvent

from PyQt5.QtWebEngineWidgets import QWebEngineView

from PyQt5.QtSvg import QGraphicsSvgItem
#
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# from matplotlib.figure import Figure
#import matplotlib.pyplot as plt
#
import sys
from math import log10

import fitz
try:
    from . import core
except ImportError:
    import core


class SvgView(QWebEngineView):
    def __init__(self):
        super().__init__()
        self._original_paths = None
        self._selected_path = None
        self._previous_pos = (0, 0)
        self.loadFinished.connect(self._scroll_to_previous)
        self._pressed_position = None

    def _scroll_to_previous(self):
        page = self.page()
        # page.runJavaScript('window.scrollTo({}, "smooth");'.format(
        #    self._previous_pos[0]))

    def loadSvg(self, txt):
        self._original_paths = core.Paths(txt)
        self.setHtml(self._original_paths.svg)

    def setHtml(self, txt):
        self.scroll(0, 0)
        pos = self.page().scrollPosition()
        self._previous_pos = pos.x(), pos.y()
        super().setHtml(txt)

    def svd_position(self, pos):
        """
        Return the svd-oriented position from the current position

        pos: np.array
        """
        page = self.page().scrollPosition()
        scroll = np.array([page.x(), page.y()])
        zoomscale = self.zoomFactor()
        view_x = np.array([self.pos().x(), self.pos().y()])
        pos = (scroll + pos - view_x) / zoomscale
        # convert it to inch
        dpi = ([self.physicalDpiX(), self.physicalDpiY()])
        return pos / dpi

    def onPress(self, event):
        self._pressed_position = self.svd_position(
            np.array([event.pos().x(), event.pos().y()]))

    def onRelease(self, event):
        current_position = self.svd_position(
            np.array([event.pos().x(), event.pos().y()]))
        if self._original_paths is not None:
            # find if there is a path inside the selected region
            self._selected_path = self._original_paths.find_inside(
                self._pressed_position, current_position)

            if self._selected_path is None:
                # consider the release position
                self._selected_path = self._original_paths.find_nearest(current_position)
            new_svd = self._original_paths.appended_svd(self._selected_path)
            self.setHtml(new_svd)

    def selected(self, use_group=False):
        if self._selected_path is None or len(self._selected_path.abs_path) == 0:
            return None
        if use_group:
            raise NotImplementedError
        else:
            return np.stack(self._selected_path.abs_path, axis=-1)


# Main Windows
class Windows(QMainWindow):

    def __init__(self):
        super().__init__()
        #
        sizeObject = QDesktopWidget().screenGeometry(-1)
        screenRatio = sizeObject.height() / sizeObject.width()
        self.title = "PyDigitizer"
        self.top = 100
        self.left = 100
        self.width = int(sizeObject.width() * 0.6)
        self.height = int(self.width * screenRatio)
        #
        self.CentralWidget = self.InitWindow()
        #
        self.show()

    def InitWindow(self):

        self.setWindowTitle(self.title)
        self.setGeometry(self.top, self.left, self.width, self.height)
        CentralWidget = MainWidget(self)
        self.setCentralWidget(CentralWidget)
        #
        return CentralWidget


# Main Widget
class MainWidget(QWidget):

    def __init__(self, parent):
        super().__init__()
        self.filename = None
        # input
        self.X0pic = None
        self.X1pic = None
        self.Y0pic = None
        self.Y1pic = None
        #
        self.X0real = None
        self.Y0real = None
        self.X1real = None
        self.Y1real = None
        #
        self.XScaleType = 'linear'
        self.YScaleType = 'linear'

        # output
        self.Xsampled = None
        self.Ysampled = None
        #
        self.x = None
        self.y = None

        (self.Page, 
        self.Xlinear,
        self.Xlog,
        self.Ylinear,
        self.Ylog,
        self.WebView,
        self.HintLabel,
        self.X0Label,
        self.Y0Label,
        self.X1Label,
        self.Y1Label) = self.initUI()

        self.show()


    def initUI(self):

        # First Column (Commands)
        # ----------------------------------
        VBoxSx1 = QGroupBox()
        LayoutSx1 = QGridLayout()
        #
        LoadFileButton = QPushButton('Load Image',self)
        LoadFileButton.clicked.connect(self.loadImage)
        LoadPageButton = QSpinBox()
        LoadPageButton.valueChanged.connect(self.reloadImage)
        LoadPageButton.setMaximum(0)
        LoadPageButton.setMinimum(0)
        #
        LayoutSx1.addWidget(LoadFileButton,0,0)
        LayoutSx1.addWidget(LoadPageButton,1,0)
        VBoxSx1.setLayout(LayoutSx1)
        # ----------------------------------
        VBoxSx2 = QGroupBox()
        VBoxSx2.setTitle('Axis values')
        LayoutSx2 = QGridLayout()
        #
        X0Button = QPushButton('Pick X0',self)
        X0Label = QLabel(self)
        X0Label.setStyleSheet(('background-color : white; color: black'))
        X1Button = QPushButton('Pick X1',self)
        X1Label = QLabel(self)
        X1Label.setStyleSheet(('background-color : white; color: black'))
        Y0Button = QPushButton('Pick Y0',self)
        Y0Label = QLabel(self)
        Y0Label.setStyleSheet(('background-color : white; color: black'))
        Y1Button = QPushButton('Pick Y1',self)
        Y1Label = QLabel(self)
        Y1Label.setStyleSheet(('background-color : white; color: black'))
        #
        X0Button.clicked.connect(self.select_X0)
        X1Button.clicked.connect(self.select_X1)
        Y0Button.clicked.connect(self.select_Y0)
        Y1Button.clicked.connect(self.select_Y1)
        #
        LayoutSx2.addWidget(X0Button,0,0)
        LayoutSx2.addWidget(X0Label,0,1)
        LayoutSx2.addWidget(X1Button,1,0)
        LayoutSx2.addWidget(X1Label,1,1)
        LayoutSx2.addWidget(Y0Button,2,0)
        LayoutSx2.addWidget(Y0Label,2,1)
        LayoutSx2.addWidget(Y1Button,3,0)
        LayoutSx2.addWidget(Y1Label,3,1)
        #
        VBoxSx2.setLayout(LayoutSx2)
        # ----------------------------------
        VBoxSx3 = QGroupBox()
        VBoxSx3.setTitle('x scale')
        LayoutSx3 = QGridLayout()
        Xlinear = QRadioButton('linear')
        Xlinear.setChecked(True)
        Xlolg = QRadioButton('log')
        LayoutSx3.addWidget(Xlinear,0,0)
        LayoutSx3.addWidget(Xlolg,0,1)
        #
        Xlinear.clicked.connect(self.setXScaleType)
        Xlolg.clicked.connect(self.setXScaleType)
        #
        VBoxSx3.setLayout(LayoutSx3)
        # ----------------------------------
        VBoxSx4 = QGroupBox()
        VBoxSx4.setTitle('y scale')
        LayoutSx4 = QGridLayout()
        Ylinear = QRadioButton('linear')
        Ylinear.setChecked(True)
        Ylog = QRadioButton('log')
        LayoutSx4.addWidget(Ylinear,0,0)
        LayoutSx4.addWidget(Ylog,0,1)
        #
        Ylinear.clicked.connect(self.setYScaleType)
        Ylog.clicked.connect(self.setYScaleType)
        #
        VBoxSx4.setLayout(LayoutSx4)
        # ----------------------------------
        VBoxSx5 = QGroupBox()
        LayoutSx5 = QGridLayout()

        PickPointButton = QPushButton('find group',self)
        PickPointButton.clicked.connect(self.findGroup)

        LayoutSx5.addWidget(PickPointButton,0,0)
        VBoxSx5.setLayout(LayoutSx5)
        # ----------------------------------
        VBoxSx6 = QGroupBox()
        LayoutSx6 = QGridLayout()

        SaveToFileButton = QPushButton('Save to File',self)
        SaveToFileButton.clicked.connect(self.saveToFile)
        
        LayoutSx6.addWidget(SaveToFileButton,0,0)
        VBoxSx6.setLayout(LayoutSx6)
        # ----------------------------------
        VBoxSx7 = QGroupBox()
        LayoutSx7 = QGridLayout()
        HintLabel = ScrollLabel(self)
        HintLabel.setMaximumHeight(40)
        HintLabel.setStyleSheet(('background-color : white; color: black'))
        HintLabel.setWordWrap(True)
        HintLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        HintLabel.setText('')

        LayoutSx7.addWidget(HintLabel,1,0)
        VBoxSx7.setLayout(LayoutSx7)
        # ----------------------------------
        # Second Column (Figure)
        VBoxDx1 = QGroupBox()
        Layout2 = QGridLayout()
        WebView = SvgView()
        self._glwidget = []
        WebView.installEventFilter(self)
        
        Layout2.addWidget(WebView,1,0)
        VBoxDx1.setLayout(Layout2)
        # ----------------------------------
        # ----------------------------------
        # Compose Windows
        windowLayout = QGridLayout()
        windowLayout.addWidget(VBoxSx1, 0, 0)
        windowLayout.addWidget(VBoxSx2, 1, 0)
        windowLayout.addWidget(VBoxSx3, 2, 0)
        windowLayout.addWidget(VBoxSx4, 3, 0)
        windowLayout.addWidget(VBoxSx5, 4, 0)
        windowLayout.addWidget(VBoxSx6, 5, 0)
        windowLayout.addWidget(VBoxSx7, 6, 0, 1, 2)
        #
        windowLayout.addWidget(VBoxDx1, 0, 1, 6, 1)
        # Stretches
        windowLayout.setColumnStretch(0, 0)
        windowLayout.setColumnStretch(1, 2)
        windowLayout.setRowStretch(0, 1)
        windowLayout.setRowStretch(1, 1)
        windowLayout.setRowStretch(2, 1)
        windowLayout.setRowStretch(3, 1)
        windowLayout.setRowStretch(4, 1)
        windowLayout.setRowStretch(5, 1)
        windowLayout.setRowStretch(6, 0)
        #
        self.setLayout(windowLayout)
        # ----------------------------------
        # ----------------------------------
        return (LoadPageButton, 
                Xlinear, Xlolg, Ylinear, Ylog, WebView, HintLabel,
                X0Label, Y0Label, X1Label, Y1Label)

    def loadImage(self):
        self.filename, _ = QFileDialog.getOpenFileName()
        self.reloadImage()

    def reloadImage(self):
        if self.filename is None:
            return
        page = self.Page.value()
        try:
            n_page = core.n_pages(self.filename) - 1
            page = np.minimum(page, n_page)
            txt = core._to_svg(self.filename, page)
            self.WebView.loadSvg(txt)
            self.Page.setMaximum(n_page)
        except RuntimeError:
            # Not a valid file
            self.HintLabel.setText('invalid file')        

    def eventFilter(self, source, event):
        if (event.type() == QEvent.ChildAdded and
            source is self.WebView and
            event.child().isWidgetType()):
            if event.child() not in self._glwidget:
                self._glwidget.append(event.child())
                self._glwidget[-1].installEventFilter(self)
        elif (event.type() == QEvent.MouseButtonPress and
              source in self._glwidget):
            self.WebView.onPress(event)
        elif (event.type() == QEvent.MouseButtonRelease and
              source in self._glwidget):
            self.WebView.onRelease(event)
        
        self._display_value()
        return super().eventFilter(source, event)

    def _select(self, x_or_y):
        idx = {'x': 0, 'y': 1}[x_or_y]
        self.HintLabel.setText('Click at a tick on {} axis.'.format(x_or_y))
        self.WebView.setFocusPolicy( Qt.ClickFocus )
        self.WebView.setFocus()

        pic_val = self.WebView._selected_path.center[idx]

        self.HintLabel.setText('Provide the corresponding {} value.'.format(x_or_y))
        real_val, okPressed = QInputDialog.getDouble(
            self, "Set {} value".format(x_or_y), 
            "Value:", value=0, decimals=4)
        self.HintLabel.setText('')
        return pic_val, real_val

    def select_X0(self):
        if self.WebView._selected_path is not None:
            pic, real = self._select('x')
            self.X0pic = pic
            self.X0real = real
            self.X0Label.setText(str(self.X0real))

    def select_X1(self):
        if self.WebView._selected_path is not None:
            pic, real = self._select('x')
            self.X1pic = pic
            self.X1real = real
            self.X1Label.setText(str(self.X1real))

    def select_Y0(self):
        if self.WebView._selected_path is not None:
            pic, real = self._select('y')
            self.Y0pic = pic
            self.Y0real = real
            self.Y0Label.setText(str(self.Y0real))

    def select_Y1(self):
        if self.WebView._selected_path is not None:
            pic, real = self._select('y')
            self.Y1pic = pic
            self.Y1real = real
            self.Y1Label.setText(str(self.Y1real))

    def setXScaleType(self):
        if self.Xlinear.isChecked():
            self.XScaleType = 'linear'
        elif self.Xlog.isChecked():
            self.XScaleType = 'log'

    def setYScaleType(self):
        if self.Ylinear.isChecked():
            self.YScaleType = 'linear'
        elif self.Ylog.isChecked():
            self.YScaleType = 'log'

    def _convert(self, x, x0pic, x1pic, x0real, x1real, use_log=False):
        if use_log:
            val = self._convert(
                x, x0pic, x1pic, 
                np.log10(x0real), np.log10(x1real), use_log=False)
            return 10**val
        return (x - x0pic) / (x1pic - x0pic) * (x1real - x0real) + x0real

    def convert_x(self, x):
        return self._convert(
            x, self.X0pic, self.X1pic, self.X0pic, self.X1pic, 
            self.XScaleType == 'log')

    def convert_y(self, y):
        return self._convert(
            y, self.Y0pic, self.Y1pic, self.Y0pic, self.Y1pic, 
            self.YScaleType == 'log')

    def _display_value(self):
        if not hasattr(self, 'WebView'):
            return
        xy = self.WebView.selected()
        if xy is None:
            return
        self.Xsampled, self.Ysampled = xy[0], xy[1]

        if all(v is not None for v in [
            self.X0pic, self.X1pic, self.Y0pic, self.Y1pic,
            self.X0real, self.Y0real, self.X1real, self.Y1real]
        ):
            self.HintLabel.setText(
                '**** calibrated values ****\n{}'.format(
                    np.stack([
                        self.convert_x(self.Xsampled), self.convert_y(self.Ysampled)
                    ], axis=1))
            )            
        else:
            self.HintLabel.setText(
                '#### raw values ####\n{}'.format(
                    np.stack([self.Xsampled, self.Ysampled], axis=1))
            )            

    def findGroup(self):

        self.HintLabel.setText('Pick points: please note that if you zoom, '
                               'the first click (for zooming) is registered. '
                               'Remove it with backspace.')

        self.FigCanvas.setFocusPolicy( Qt.ClickFocus )
        self.FigCanvas.setFocus()
        pt = self.FigCanvas.figure.ginput(n=-1, timeout=-1)

        self.Xsampled = []
        self.Ysampled = []

        for ptx, pty in pt:
            self.Xsampled.append(ptx)
            self.Ysampled.append(pty)

        self.HintLabel.setText('')

    def saveToFile(self):
        for x, label in [
            (self.X0pic, 'X0'), (self.X1pic, 'X1'),
            (self.X0real, 'X0'), (self.X1real, 'X1'),
            (self.Y0pic, 'Y0'), (self.Y1pic, 'Y1'),
            (self.Y0real, 'Y0'), (self.Y1real, 'Y1'),
            (self.Xsampled, 'data'), (self.Ysampled, 'data'),
        ]:
            if x is None:
                self.HintLabel.setText('Please pick {}'.format(label))
                return

        fname , _ = QFileDialog.getSaveFileName(self)
        array = np.stack([
            self.convert_x(self.Xsampled), self.convert_y(self.Ysampled)
        ], axis=1)
        np.savetxt(fname, array)


class ScrollLabel(QScrollArea):
    # contructor
    def __init__(self, *args, **kwargs):
        QScrollArea.__init__(self, *args, **kwargs)

        # making widget resizable
        self.setWidgetResizable(True)

        # making qwidget object
        content = QWidget(self)
        self.setWidget(content)

        # vertical box layout
        lay = QVBoxLayout(content)

        # creating label
        self.label = QLabel(content)

        # setting alignment to the text
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)

    # the setText method
    def setText(self, text):
        # setting text to the label
        self.label.setText(text)
    
    def setWordWrap(self, flag):
        self.label.setWordWrap(flag)

    def setTextInteractionFlags(self, flag):
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)


# Start App
if __name__ == '__main__':
    App = QApplication(sys.argv)
    window = Windows()
    sys.exit(App.exec())
