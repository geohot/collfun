import sys
import flask
import math
from shafactors import *

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget, QFrame)

selected = None
hasBackgroundColor = []

class VariableLabel(QLabel):
  def __init__(self, variable, parent=None):
    QLabel.__init__(self, parent)
    self.variable = variable
    self.variable.qt = self
    self.variable.update()

  def mouseReleaseEvent(self, event):
    global selected, hasBackgroundColor

    print 'clicked %s %s' % (self.variable.name, str(self.variable.probs))
    for a in hasBackgroundColor:
      a.setStyleSheet('')
    hasBackgroundColor = []
    selected = self
    neighbors = self.variable.neighbors(2)
    for k in neighbors:
      c = neighbors[k] * 100
      if k.qt != None:
        k.qt.setStyleSheet('QLabel { background-color: #%2.2X%2.2X%2.2X }' % (c, c, 255))
        hasBackgroundColor.append(k.qt)
    self.setStyleSheet('QLabel { background-color: #%2.2X%2.2X%2.2X }' % (255, 0, 0))

class SHA1FactorGraph(QWidget):
  def __init__(self, rounds=80, bits=32, extended=False, parent=None):
    super(SHA1FactorGraph, self).__init__(parent)

    # construct the graph
    self.rounds = rounds
    self.bits = bits
    self.G = build_sha1_FactorGraph(self.rounds, self.bits)
    self.puLabels = []

    # dot
    #self.G.dot("/tmp/out.dot")

    # font to use
    font = QtGui.QFont('Courier New', 10, QtGui.QFont.Light)

    # i
    iLayout = QGridLayout()
    iLayout.setSpacing(0)

    # display the Ws
    WLayout = QGridLayout()
    WLayout.setSpacing(0)
    for i in range(0,4):
      WLayout.addWidget(QLabel(""), i, 0)
    WLayout.addWidget(QLabel(""), self.rounds+4, 0)

    for i in range(self.rounds):
      for j in range(self.bits):
        widget = VariableLabel(self.G["W_%d_%d" % (i,j)])
        widget.setFont(font)
        WLayout.addWidget(widget, i+4, self.bits-j-1)

      self.puLabels.append(QLabel(""))
      self.puLabels[-1].setFont(font)
      WLayout.addWidget(self.puLabels[-1], i+4, self.bits+1)

    # display the As
    ALayout = QGridLayout()
    ALayout.setSpacing(0)
    for i in range(-4, self.rounds+1):
      widget = QLabel("%2d" % i)
      widget.setFont(font)
      iLayout.addWidget(widget, i+4, 0)
      for j in range(self.bits):
        widget = VariableLabel(self.G["A_%d_%d" % (i,j)])
        widget.setFont(font)
        ALayout.addWidget(widget, i+4, self.bits-j-1)

    Buttons = QVBoxLayout()

    computeButton = QPushButton("&Compute")
    computeButton.clicked.connect(self.compute)
    Buttons.addWidget(computeButton)

    puButton = QPushButton("&Update")
    puButton.clicked.connect(self.update)
    Buttons.addWidget(puButton)

    resetButton = QPushButton("&Reset")
    resetButton.clicked.connect(self.reset)
    Buttons.addWidget(resetButton)

    quitButton = QPushButton("&Quit")
    quitButton.clicked.connect(QApplication.quit)
    Buttons.addWidget(quitButton)

    mainLayout = QHBoxLayout()
    mainLayout.addLayout(iLayout)
    mainLayout.addLayout(ALayout)
    mainLayout.addLayout(WLayout)
    mainLayout.addLayout(Buttons)

    if extended:
      # line
      toto = QFrame()
      toto.setFrameShape(QFrame.VLine)
      toto.setFrameShadow(QFrame.Sunken)

      # display the Fs
      FLayout = QGridLayout()
      FLayout.setSpacing(0)
      for i in range(0,4):
        FLayout.addWidget(QLabel(""), i, 0)
      FLayout.addWidget(QLabel(""), self.rounds+4, 0)

      for i in range(self.rounds):
        for j in range(self.bits):
          widget = VariableLabel(self.G["F_%d_%d" % (i,j)])
          widget.setFont(font)
          FLayout.addWidget(widget, i+4, self.bits-j-1)

      # display the Cs
      CLayout = QGridLayout()
      CLayout.setSpacing(0)
      for i in range(0,4):
        CLayout.addWidget(QLabel(""), i, 0)
      CLayout.addWidget(QLabel(""), self.rounds+4, 0)

      for i in range(self.rounds):
        for j in range(self.bits-1):
          widget = VariableLabel(self.G["C_%d_%d" % (i,j)])
          widget.setFont(font)
          CLayout.addWidget(widget, i+4, (self.bits-1)-j-1)

      mainLayout.addWidget(toto)
      mainLayout.addLayout(FLayout)
      mainLayout.addLayout(CLayout)

    self.setLayout(mainLayout)
    self.setWindowTitle("SHA1 Factor Graph")

    self.reset()

  def keyPressEvent(self, qKeyEvent):
    print "key"
  
  def compute(self):
    self.G.compute()

  def update(self):
    self.G.compute()

    #for i in range(1, self.rounds+1):
    for i in range(1, 2):
      # save the probabilities of the round
      saved = []
      for j in range(self.bits):
        saved.append(self.G["A_%d_%d" % (i, j)].probs)
        
      # read off the Pu
      pu = 0.0
      for j in range(self.bits):
        # reset the jth bit
        if j != 0:
          self.G["C_%d_%d" % (i-1, j-1)].reset()
        self.G["F_%d_%d" % (i-1, j)].reset()
        self.G["A_%d_%d" % (i, j)].reset()

        # compute the new probs
        self.G.compute()

        # add off the new probs
        probs = self.G["A_%d_%d" % (i, j)].probs[:]
        ret = 0.0
        new_probs = [0.0]*4
        for k in range(len(saved[j])):
          if saved[j][k] > 0.0:
            new_probs[k] = probs[k]
            ret += probs[k]
        try:
          pu += math.log(ret, 2)
        except:
          pu += float("-inf")

        # must normalize
        self.G["A_%d_%d" % (i, j)].setProbs(new_probs)
        print probs, self.G["A_%d_%d" % (i, j)].probs

        

        #print i, j, pu, saved[j], probs
      #print i, pu
      self.puLabels[i-1].setText("  %6.2f" % pu)

      """"
      # restore the old probs
      for j in range(self.bits):
        self.G["A_%d_%d" % (i, j)].setProbs(saved[j])
      """

  
  def reset(self):
    self.G.reset()

    # load the graph with example data
    #load_sha1_characteristic(self.G, "dc_char")
    load_sha1_characteristic(self.G, "test_char")
    #load_sha1_example_data(self.G)


if __name__ == "__main__":
  import sys
  from PyQt5.QtWidgets import QApplication

  app = QApplication(sys.argv)
  
  #g = SHA1FactorGraph(80, 4)
  g = SHA1FactorGraph(64, 32, True)
  #g = SHA1FactorGraph(64, 32)
  #g = SHA1FactorGraph(80, 32)
  g.show()

  sys.exit(app.exec_()) 


