"""
I learned how to use Qt from https://github.com/giaccone/PyDigitizer
"""
import numpy as np
# modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QGroupBox, QPushButton, QFileDialog, QSizePolicy,
    QRadioButton, QInputDialog, QLabel, QDesktopWidget,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem)
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
        self._selected_paths = []

    def loadSvg(self, txt):
        self._original_paths = core.Paths(txt)
        self.setHtml(self._original_paths.svg)

    def setHtml(self, txt):
        self.scroll(0, 0)
        page = self.page()
        pos = page.scrollPosition()
        super().setHtml(txt)
        page.runJavaScript('window.scrollTo({}, {});'.format(pos.x(), pos.y()))

    def svd_position(self, pos):
        """
        Return the svd-oriented position from the current position

        pos: np.array
        """
        page = self.page().scrollPosition()
        scroll = np.array([page.x(), page.y()])
        zoomscale = self.zoomFactor()
        view_x = np.array([self.pos().x(), self.pos().y()])
        pos = (scroll + pos) / zoomscale
        # convert it to inch
        dpi = ([self.physicalDpiX(), self.physicalDpiY()])
        print(view_x, pos / dpi)
        return pos / dpi

    def onClick(self, event):
        pos = event.pos()
        pos = self.svd_position(np.array([pos.x(), pos.y()]))
        if self._original_paths is not None:
            path = self._original_paths.find_nearest(pos)
            new_svd = self._original_paths.appended_svd(path)
            self.setHtml(new_svd)


# FigureCanvas
class MplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=4, dpi=100, filename=None):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        self.compute_initial_figure(filename)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self,  filename):

        if filename is None:
            self.axes.clear()
        else:
            img = plt.imread(filename)
            self.axes.clear()
            self.axes.imshow(img)
            self.axes.axis('off')


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
        self.width = sizeObject.width() * 0.6
        self.height = self.width * screenRatio
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
        # input
        self.Xpic_min = None
        self.Xpic_max = None
        self.Ypic_min = None
        self.Ypic_max = None
        #
        self.Xreal_min = None
        self.Yreal_min = None
        self.Xreal_max = None
        self.Yreal_max = None
        #
        self.XScaleType = 'linear'
        self.YScaleType = 'linear'

        # output
        self.Xsampled = None
        self.Ysampled = None
        #
        self.x = None
        self.y = None

        (self.Xlinear,
        self.Xlog,
        self.Ylinear,
        self.Ylog,
        self.WebView,
        self.HintLabel,
        self.XminLabel,
        self.YminLabel,
        self.XmaxLabel,
        self.YmaxLabel) = self.initUI()

        self.show()


    def initUI(self):

        # First Column (Commands)
        # ----------------------------------
        VBoxSx1 = QGroupBox()
        LayoutSx1 = QGridLayout()
        #
        LoadFileButton = QPushButton('Load Image',self)
        LoadFileButton.clicked.connect(self.loadImage)
        #
        LayoutSx1.addWidget(LoadFileButton,0,0)
        VBoxSx1.setLayout(LayoutSx1)
        # ----------------------------------
        VBoxSx2 = QGroupBox()
        VBoxSx2.setTitle('Picture limits')
        LayoutSx2 = QGridLayout()
        #
        XminButton = QPushButton('Pick X_min',self)
        XminLabel = QLabel(self)
        XminLabel.setStyleSheet(('background-color : white; color: black'))
        YminButton = QPushButton('Pick Y_min',self)
        YminLabel = QLabel(self)
        YminLabel.setStyleSheet(('background-color : white; color: black'))
        XmaxButton = QPushButton('Pick X_max',self)
        XmaxLabel = QLabel(self)
        XmaxLabel.setStyleSheet(('background-color : white; color: black'))
        YmaxButton = QPushButton('Pick Y_max',self)
        YmaxLabel = QLabel(self)
        YmaxLabel.setStyleSheet(('background-color : white; color: black'))
        #
        XminButton.clicked.connect(self.pickXmin)
        YminButton.clicked.connect(self.pickYmin)
        XmaxButton.clicked.connect(self.pickXmax)
        YmaxButton.clicked.connect(self.pickYmax)
        #
        LayoutSx2.addWidget(XminButton,0,0)
        LayoutSx2.addWidget(XminLabel,0,1)
        LayoutSx2.addWidget(YminButton,1,0)
        LayoutSx2.addWidget(YminLabel,1,1)
        LayoutSx2.addWidget(XmaxButton,2,0)
        LayoutSx2.addWidget(XmaxLabel,2,1)
        LayoutSx2.addWidget(YmaxButton,3,0)
        LayoutSx2.addWidget(YmaxLabel,3,1)
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

        PickPointButton = QPushButton('Pick Points',self)
        PickPointButton.clicked.connect(self.pickPoints)

        LayoutSx5.addWidget(PickPointButton,0,0)
        VBoxSx5.setLayout(LayoutSx5)
        # ----------------------------------
        VBoxSx6 = QGroupBox()
        LayoutSx6 = QGridLayout()

        SaveToFileButton = QPushButton('Save to File',self)
        TestDataButton = QPushButton('Test data',self)
        SaveToFileButton.clicked.connect(self.saveToFile)
        TestDataButton.clicked.connect(self.testData)

        LayoutSx6.addWidget(SaveToFileButton,0,0)
        LayoutSx6.addWidget(TestDataButton,1,0)
        VBoxSx6.setLayout(LayoutSx6)
        # ----------------------------------
        VBoxSx7 = QGroupBox()
        LayoutSx7 = QGridLayout()
        HintLabel = QLabel(self)
        HintLabel.setMaximumHeight(40)
        HintLabel.setStyleSheet(('background-color : white; color: black'))
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
        return (Xlinear, Xlolg, Ylinear, Ylog, WebView, HintLabel,
                XminLabel, YminLabel, XmaxLabel, YmaxLabel)

    def loadImage(self):
        filename, _ = QFileDialog.getOpenFileName()
        txt = core._to_svg(filename, 0)
        self.WebView.loadSvg(txt)

    def eventFilter(self, source, event):
        if (event.type() == QEvent.ChildAdded and
            source is self.WebView and
            event.child().isWidgetType()):
            if event.child() not in self._glwidget:
                self._glwidget.append(event.child())
                self._glwidget[-1].installEventFilter(self)
        elif (event.type() == QEvent.MouseButtonPress and
              source in self._glwidget):
            self.WebView.onClick(event)
        return super().eventFilter(source, event)

    def pickXmin(self):

        self.HintLabel.setText('Click at a tick on x axis.')
        self.WebView.setFocusPolicy( Qt.ClickFocus )
        self.WebView.setFocus()
        # pt = self.WebView.figure.ginput(n=1)
        # self.Xpic_min = pt[0][0]

        self.HintLabel.setText('Provide the minimum x value.')
        self.Xreal_min, okPressed = QInputDialog.getDouble(self, "Set X_min value", "Value:", value=0, decimals=4)
        self.HintLabel.setText('')
        self.XminLabel.setText(str(self.Xreal_min))

    def pickYmin(self):

        self.HintLabel.setText('Click at a point having minimum y value.')
        self.FigCanvas.setFocusPolicy( Qt.ClickFocus )
        self.FigCanvas.setFocus()
        pt = self.FigCanvas.figure.ginput(n=1)
        self.Ypic_min = pt[0][1]

        self.HintLabel.setText('Provide the minimum y value.')
        self.Yreal_min, okPressed = QInputDialog.getDouble(self, "Set Y_min value", "Value:", value=0, decimals=4)
        self.HintLabel.setText('')
        self.YminLabel.setText(str(self.Yreal_min))

    def pickXmax(self):

        self.HintLabel.setText('Click at a point having maximum x value.')
        self.FigCanvas.setFocusPolicy( Qt.ClickFocus )
        self.FigCanvas.setFocus()
        pt = self.FigCanvas.figure.ginput(n=1)
        self.Xpic_max = pt[0][0]

        self.HintLabel.setText('Provide the maximum x value.')
        self.Xreal_max, okPressed = QInputDialog.getDouble(self, "Set X_max value", "Value:", value=0, decimals=4)
        self.HintLabel.setText('')
        self.XmaxLabel.setText(str(self.Xreal_max))

    def pickYmax(self):

        self.HintLabel.setText('Click at a point having maximum y value.')
        self.FigCanvas.setFocusPolicy( Qt.ClickFocus )
        self.FigCanvas.setFocus()
        pt = self.FigCanvas.figure.ginput(n=1)
        self.Ypic_max = pt[0][1]

        self.HintLabel.setText('Provide the maximum y value.')
        self.Yreal_max, okPressed = QInputDialog.getDouble(self, "Set Y_max value", "Value:", value=0, decimals=4)
        self.HintLabel.setText('')
        self.YmaxLabel.setText(str(self.Yreal_max))

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

    def pickPoints(self):

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

        if self.Xpic_min is None:
            self.HintLabel.setText('Please pick X_min')
            return
        elif self.Ypic_min is None:
            self.HintLabel.setText('Please pick Y_min')
            return
        elif self.Xpic_max is None:
            self.HintLabel.setText('Please pick X_max')
            return
        elif self.Ypic_max is None:
            self.HintLabel.setText('Please pick Y_max')
            return
        elif self.Xreal_min is None:
            self.HintLabel.setText('Please pick X_min')
            return
        elif self.Yreal_min is None:
            self.HintLabel.setText('Please pick Y_min')
            return
        elif self.Xreal_max is None:
            self.HintLabel.setText('Please pick X_max')
            return
        elif self.Yreal_max is None:
            self.HintLabel.setText('Please pick Y_max')
            return
        elif self.Xsampled is None:
            self.HintLabel.setText('Please pick data')
            return
        elif self.Ysampled is None:
            self.HintLabel.setText('Please pick data')
            return
        else:
            self.HintLabel.setText('')

        self.x = []
        self.y = []

        if self.XScaleType is 'linear':
            for xs in self.Xsampled:
                self.x.append(self.Xreal_min + (self.Xreal_max - self.Xreal_min) / (self.Xpic_max - self.Xpic_min) * ( xs - self.Xpic_min))
        elif self.XScaleType is 'log':
            Xreal_min = log10(self.Xreal_min)
            Xreal_max = log10(self.Xreal_max)
            for xs in self.Xsampled:
                self.x.append(10 ** (Xreal_min + (xs - self.Xpic_min)/(self.Xpic_max - self.Xpic_min) * (Xreal_max - Xreal_min)))

        if self.YScaleType is 'linear':
            for ys in self.Ysampled:
                self.y.append(self.Yreal_min + (self.Yreal_max - self.Yreal_min) / (self.Ypic_max - self.Ypic_min) * ( ys - self.Ypic_min))
        elif self.YScaleType is 'log':
            Yreal_min = log10(self.Yreal_min)
            Yreal_max = log10(self.Yreal_max)
            for ys in self.Ysampled:
                self.y.append(10 ** (Yreal_min + (ys - self.Ypic_min)/(self.Ypic_max - self.Ypic_min) * (Yreal_max - Yreal_min)))

        fname , _ = QFileDialog.getSaveFileName(self)

        with open(fname, 'w') as fid:
            for xpt, ypt in zip(self.x, self.y):
                fid.write("{} {}\n".format(xpt, ypt))

    def testData(self):

        filename, _ = QFileDialog.getOpenFileName()

        xs = []
        ys = []
        with open(filename, 'r') as fid:
            for line in fid:
                line = line.split(' ')
                xs.append(float(line[0]))
                ys.append(float(line[1]))
        hf = plt.figure()
        plt.plot(xs, ys,'C0-o')
        ax = hf.gca()
        ax.set_xlabel('x variable')
        ax.set_ylabel('y variable')
        ax.set_xscale(self.XScaleType)
        ax.set_yscale(self.YScaleType)
        plt.show()


# Start App
if __name__ == '__main__':
    App = QApplication(sys.argv)
    window = Windows()
    sys.exit(App.exec())
