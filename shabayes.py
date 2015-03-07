import sys
import networkx as nx
import flask
import time
import math
from factorgraph import *

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget, QFrame)

# Unique Factors
#   f_if, f_maj, f_xor -- (4,4,4,4)         = 256
#   add_0, add_1       -- (25,25,4,4,4,4,4) = 640,000
#   xor5               -- (4,4,4,4,4)       = 1024

start = time.time()

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_if(b,c,d):
  return d ^ (b & (c ^ d))

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_maj(b,c,d):
  return b&c ^ b&d ^ c&d

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_xor(b,c,d):
  return b^c^d

# w, a, f, e, c_in -> c_out, o
@factor([2,2,2,2], 2, True)
def add_0(w, a, f, e):
  return (w+a+f+e+0) & 1
@factor([2,2,2,2,5], 2, True)
def addc_0(w, a, f, e, c_in):
  return (w+a+f+e+c_in+0) & 1
@factor([2,2,2,2], 5, True)
def carry_0(w, a, f, e):
  return (w+a+f+e+0) >> 1
@factor([2,2,2,2,5], 5, True)
def carryc_0(w, a, f, e, c_in):
  return (w+a+f+e+c_in+0) >> 1

# w, a, f, e, c_in -> c_out, o
@factor([2,2,2,2], 2, True)
def add_1(w, a, f, e):
  return (w+a+f+e+1) & 1
@factor([2,2,2,2,5], 2, True)
def addc_1(w, a, f, e, c_in):
  return (w+a+f+e+c_in+1) & 1
@factor([2,2,2,2], 5, True)
def carry_1(w, a, f, e):
  return (w+a+f+e+1) >> 1
@factor([2,2,2,2,5], 5, True)
def carryc_1(w, a, f, e, c_in):
  return (w+a+f+e+c_in+1) >> 1

# x1, x2, x3, x4 -> x5
@factor([2,2,2,2], 2, True)
def xor5(x1, x2, x3, x4):
  return x1 ^ x2 ^ x3 ^ x4

print "built factor matrices in %f s" % (time.time()-start)

# Bit Random Variables
#   W_(0,79)_(0,31)   -- 80*32 --  4 states
#   A_(-4, 80)_(0,31) -- 85*32 --  4 states
#   F_(0,79)_(0,31)   -- 80*32 --  4 states
#   C_(0,79)_(0,30)   -- 80*31 -- 25 states

def build_sha1_FactorGraph(rounds, bits):
  G = FactorGraph()

  # add W's, F's, C's
  for i in range(rounds):
    for j in range(bits):
      G.addVariable("W_%d_%d" % (i,j), 2*2)
      G.addVariable("F_%d_%d" % (i,j), 2*2)
    for j in range(bits-1):
      G.addVariable("C_%d_%d" % (i,j), 5*5)

  # add A's
  for i in range(-4, rounds+1):
    for j in range(bits):
      G.addVariable("A_%d_%d" % (i,j), 2*2)

  # add linear W factors
  for i in range(16, rounds):
    for j in range(bits):
      G.addFactor(xor5, [
        "W_%d_%d" % (i-16, j),
        "W_%d_%d" % (i-14, j),
        "W_%d_%d" % (i-8, j),
        "W_%d_%d" % (i-3, j),
        "W_%d_%d" % (i, (j+1) % bits)])

  # add boolean F factors
  for i in range(rounds):
    fxn = [f_if, f_xor, f_maj, f_xor][i/20]
    for j in range(bits):
      G.addFactor(fxn, [
        "A_%d_%d" % (i-1, j),
        "A_%d_%d" % (i-2, (j+2) % bits),
        "A_%d_%d" % (i-3, (j+2) % bits),
        "F_%d_%d" % (i, j)])

  # add addition bullshit
  for i in range(rounds):
    k = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]
    j = 0
    fxn = [add_0, add_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+2) % bits),
      "A_%d_%d" % (i+1, j)])
    fxn = [carry_0, carry_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+2) % bits),
      "C_%d_%d" % (i, j)])
    for j in range(1, bits):
      fxn = [addc_0, addc_1][(k>>j)&1]
      G.addFactor(fxn, [
        "W_%d_%d" % (i, j),
        "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
        "F_%d_%d" % (i, j),
        "A_%d_%d" % (i-4, (j+2) % bits),
        "C_%d_%d" % (i, j-1),
        "A_%d_%d" % (i+1, j)])
      if j != bits-1:
        fxn = [carryc_0, carryc_1][(k>>j)&1]
        G.addFactor(fxn, [
          "W_%d_%d" % (i, j),
          "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
          "F_%d_%d" % (i, j),
          "A_%d_%d" % (i-4, (j+2) % bits),
          "C_%d_%d" % (i, j-1),
          "C_%d_%d" % (i, j)])

  return G


def load_sha1_example_data(G):
  W_hello = [1751477356, 1870659584, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40]
  A_iv = [256608195, 1086935512, 1659597818, 4023233417, 1732584193]

  for i in range(len(W_hello)):
    for j in range(32):
      try:
        G["W_%d_%d" % (i,j)].fix( ((W_hello[i]>>j)&1) * 3 )
      except:
        pass

  for i in range(len(A_iv)):
    for j in range(32):
      try:
        G["A_%d_%d" % (i-4,j)].fix( ((A_iv[i]>>j)&1) * 3)
      except:
        pass


def load_sha1_characteristic(G, name):
  a = []
  w = []
  i = 0
  for ln in open(name).read().split("\n"):
    lnn = ln.split(" ")
    if len(lnn) > 1:
      # a
      for j,c in zip(range(32), lnn[1]):
        G["A_%d_%d" % (i-4,31-j)].fix(c)

    if len(lnn) > 2:
      # w
      for j,c in zip(range(32), lnn[2]):
        G["W_%d_%d" % (i-4,31-j)].fix(c)
    i += 1


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


