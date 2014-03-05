# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import pyte


class Vt100ConsoleWidget(QWidget):
    def __init__(self, parent=None):
        super(Vt100ConsoleWidget, self).__init__(parent)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.ClickFocus)

        self.fontFamily = "Monaco"
        self.fontVerticalSize = 12
        self.fontVerticalSpacing = 3
        self.fontHorizontalSize = 8
        self.fontHorizontalSpacing = 0
        self.frameSize = 2

        self.columns = 80
        self.rows = 25

        self.te_screen = pyte.Screen(self.columns, self.rows)
        self.te_stream = pyte.ByteStream()

        self.te_stream.attach(self.te_screen)

    def setData(self, data):
        if not data:
            self.te_stream.reset()
            self.te_stream.feed(b"\033[2J\033[1;1H")
        else:
            self.te_stream.feed(b"%s" % data)
        self.repaint()

    def keyPressEvent(self, ev):
        self.emit(SIGNAL("keyPressed"), ev.text())

    def paintEvent(self, ev):
        font = QFont()
        font.setFamily(self.fontFamily)
        font.setPixelSize(self.fontVerticalSize)

        p = QPainter(self)
        p.setFont(font)

        # draw black background

        p.fillRect(QRect(0, 0,
                         (self.fontHorizontalSize + self.fontHorizontalSpacing) * self.columns + self.frameSize * 2,
                         (self.fontVerticalSize + self.fontVerticalSpacing) * self.rows + self.frameSize * 2),
                   Qt.black)

        pen = QPen()
        pen.setColor(Qt.gray)
        p.setPen(pen)

        y = 0
        for line in self.te_screen.display:
            x = -1
            y += 1
            for char in line:
                x += 1

                c = self.te_screen.buffer[y-1][x]

                # draw background

                bgcolor = Qt.black
                if c.bg == 'default' or c.bg == 'black':
                    bgcolor = Qt.black
                elif c.bg == 'red':
                    bgcolor = Qt.red
                elif c.bg == 'green':
                    bgcolor = Qt.green
                elif c.bg == 'brown':
                    bgcolor = Qt.yellow
                elif c.bg == 'blue':
                    bgcolor = Qt.blue
                elif c.bg == 'magenta':
                    bgcolor = Qt.magenta
                elif c.bg == 'cyan':
                    bgcolor = Qt.cyan
                elif c.bg == 'white':
                    bgcolor = Qt.white

                p.fillRect(QRect(x * (self.fontHorizontalSize +
                                    self.fontHorizontalSpacing) + self.frameSize,
                                 (y-1) * (self.fontVerticalSize +
                                    self.fontVerticalSpacing) + self.frameSize,
                                 self.fontHorizontalSize + self.fontHorizontalSpacing,
                                self.fontVerticalSize + self.fontVerticalSpacing),
                           bgcolor)

                # draw letter

                if c.fg == 'default':
                    pen.setColor(Qt.gray)
                elif c.fg == 'black':
                    if c.bold:
                        pen.setColor(Qt.darkGray)
                    else:
                        pen.setColor(Qt.black)
                elif c.fg == 'red':
                    if c.bold:
                        pen.setColor(Qt.red)
                    else:
                        pen.setColor(Qt.darkRed)
                elif c.fg == 'green':
                    if c.bold:
                        pen.setColor(Qt.green)
                    else:
                        pen.setColor(Qt.darkGreen)
                elif c.fg == 'brown':
                    if c.bold:
                        pen.setColor(Qt.yellow)
                    else:
                        pen.setColor(Qt.darkYellow)
                elif c.fg == 'blue':
                    if c.bold:
                        pen.setColor(Qt.blue)
                    else:
                        pen.setColor(Qt.darkBlue)
                elif c.fg == 'magenta':
                    if c.bold:
                        pen.setColor(Qt.magenta)
                    else:
                        pen.setColor(Qt.darkMagenta)
                elif c.fg == 'cyan':
                    if c.bold:
                        pen.setColor(Qt.cyan)
                    else:
                        pen.setColor(Qt.darkCyan)
                elif c.fg == 'white':
                    if c.bold:
                        pen.setColor(Qt.white)
                    else:
                        pen.setColor(Qt.lightGray)

                p.setPen(pen)
                p.drawText(QPoint(x * (self.fontHorizontalSize + self.fontHorizontalSpacing) + self.frameSize,
                                  y * (self.fontVerticalSize + self.fontVerticalSpacing) + self.frameSize - 4),
                           char)

        p.drawRect(QRect(self.te_screen.cursor.x * (self.fontHorizontalSize +
                            self.fontHorizontalSpacing) + self.frameSize,
                         self.te_screen.cursor.y * (self.fontVerticalSize +
                            self.fontVerticalSpacing) + self.frameSize,
                         self.fontHorizontalSize + self.fontHorizontalSpacing,
                        self.fontVerticalSize + self.fontVerticalSpacing))
