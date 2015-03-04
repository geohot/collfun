import sys
import numpy as np
import networkx as nx
import itertools
import logging
import flask
import time
from collections import OrderedDict

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget, QFrame)

log = logging.getLogger('MyLogger')
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stderr))

class factor(object):
  """Generic factor class"""

  def __init__(self, in_dims, out_dim, double):
    self.dims = in_dims + [out_dim]
    self.double = double

  def dim_merge(self, x1, x2):
    ret = map(sum, zip(map(np.product, zip(self.dims, x1)), x2))
    #print x1, x2, ret
    return tuple(ret)

  def __call__(self, fxn):
    name = fxn.func_name
    ins = fxn.func_code.co_argcount
    dims = self.dims

    print "%8s %3d %3d" % (name, np.product(dims[0:ins]), np.product(dims)), dims[0:ins], dims[ins:]

    if self.double:
      matrix = np.zeros(map(lambda x: x*x, dims))
      #print matrix.shape
      for x1 in itertools.product(*map(range, dims[0:ins])):
        for x2 in itertools.product(*map(range, dims[0:ins])):
          matrix[self.dim_merge(x1+(fxn(*x1),), x2+(fxn(*x2),))] = 1.0
    else:
      matrix = np.zeros(dims)
      for sins in itertools.product(*map(range, dims[0:ins])):
        matrix[sins+(fxn(*sins),)] = 1.0

    return matrix


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

log.debug("built factor matrices in %f s" % (time.time()-start))

# Bit Random Variables
#   W_(0,79)_(0,31)   -- 80*32 --  4 states
#   A_(-4, 80)_(0,31) -- 85*32 --  4 states
#   F_(0,79)_(0,31)   -- 80*32 --  4 states
#   C_(0,79)_(0,30)   -- 80*31 -- 25 states

# classes are private to FactorGraph
class Variable(object):

  # is this created for each class?
  CONDITIONS = OrderedDict([
    ('#', [0.00, 0.00, 0.00, 0.00]),

    ('0', [1.00, 0.00, 0.00, 0.00]),
    ('n', [0.00, 1.00, 0.00, 0.00]),
    ('u', [0.00, 0.00, 1.00, 0.00]),
    ('1', [0.00, 0.00, 0.00, 1.00]),

    ('x', [0.00, 1.00, 1.00, 0.00]),
    ('-', [1.00, 0.00, 0.00, 1.00]),

    ('3', [1.00, 1.00, 0.00, 0.00]),
    ('5', [1.00, 0.00, 1.00, 0.00]),
    ('7', [1.00, 1.00, 1.00, 0.00]),
    ('A', [0.00, 1.00, 0.00, 1.00]),
    ('B', [1.00, 1.00, 0.00, 1.00]),
    ('C', [0.00, 0.00, 1.00, 1.00]),
    ('D', [1.00, 0.00, 1.00, 1.00]),
    ('E', [0.00, 1.00, 1.00, 1.00]),

    ('?', [1.00, 1.00, 1.00, 1.00]),
  ])

  def __init__(self, name, dim):
    self.probs = None
    self.name = name
    self.dim = dim
    self.qt = None
    self.inFactors = []

  def __str__(self):
    if self.probs == None:
      return '!'

    if self.dim != 4:
      if max(self.probs) == 0:
        return '?'
      return hex(np.argmax(self.probs))[2:]

    for c in self.CONDITIONS:
      xx = map(lambda x: x[0]*x[1], zip(self.probs, self.CONDITIONS[c])) 
      if xx == self.probs:
        #print self.probs, c, xx
        return c

    return '!'

  def neighbors(self, depth):
    ret = {self: 0}
    for i in range(1, depth+1):
      new = set()
      for k in ret:
        for factor in k.inFactors:
          #print i, factor.name, map(lambda x: x.name, factor.rvs)
          for rv in factor.rvs:
            if rv not in ret:
              new.add(rv)
      for rv in new:
        ret[rv] = i
        
    return ret

  def update(self):
    if self.qt != None:
      self.qt.setText(str(self))

  def setProbs(self, p):
    if p == None:
      self.probs = None
    else:
      self.probs = list(p / np.linalg.norm(p))
    self.update()

  def fix(self, x):
    """Concentrate all probability in one place"""
    if type(x) is str:
      probs = self.CONDITIONS[x][:]
    else:
      probs = [0.0]*self.dim
      probs[x] = 1.0
    #print x, probs
    self.setProbs(probs)

class Factor(object):
  def __init__(self, matrix, rvs):
    self.matrix = matrix
    self.rvs = rvs
    for rv in rvs:
      rv.inFactors.append(self)

  def compute(self):
    if sum(map(lambda x: x.probs != None, self.rvs)) == len(self.rvs)-1:
      mat = self.matrix
      for rv in self.rvs:
        if rv.probs != None:
          #print rv.name, rv.probs
          nmat = mat[0] * rv.probs[0]
          for i in range(1, len(rv.probs)):
            nmat += mat[i] * rv.probs[i]
          mat = nmat

      self.rvs[-1].setProbs(list(mat))
      #print "setting ", self.rvs[-1].name, self.rvs[-1].probs
      return True
    return False

# public class
class FactorGraph(object):
  def __init__(self):
    self.variables = {}
    self.factors = []
    self.mats = {}

  def __getitem__(self, key):
    return self.variables[key]

  def reset(self):
    for k in self.variables:
      self.variables[k].setProbs(None)

  def dot(self, filename):
    log.debug("start dot file generation")

    g = nx.DiGraph()
    for k in self.variables:
      g.add_node(k)

    for f in self.factors:
      for rv in f.rvs[:-1]:
        g.add_edge(rv.name, f.rvs[-1].name)

    log.debug("constructed graph has %d nodes and %d edges" % (g.number_of_nodes(), g.number_of_edges()))

    nx.write_dot(g, filename)
    log.debug("wrote %s" % filename)

  def compute(self):
    did_compute = True
    start = time.time()
    rounds = 0
    var = 0
    while did_compute:
      rounds += 1
      did_compute = False
      for f in self.factors:
        if f.compute():
          var += 1
          did_compute = True
    log.debug("%d variables computed in %d rounds in %f s" % (var, rounds, time.time()-start))

  def addVariable(self, name, dim):
    self.variables[name] = Variable(name, dim)

  def addFactor(self, fxn, rvs):
    rvs = map(lambda x: self.variables[x], rvs)
    self.factors.append(Factor(fxn, rvs))

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
        G["A_%d_%d" % (i-4,j)].fix(c)

    if len(lnn) > 2:
      # w
      for j,c in zip(range(32), lnn[1]):
        G["W_%d_%d" % (i-4,j)].fix(c)
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

    log.debug('clicked %s %s' % (self.variable.name, str(self.variable.probs)))
    for a in hasBackgroundColor:
      a.setStyleSheet('')
    hasBackgroundColor = []
    selected = self
    neighbors = self.variable.neighbors(2)
    for k in neighbors:
      c = neighbors[k] * 90
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

    resetButton = QPushButton("&Reset")
    resetButton.clicked.connect(self.reset)
    Buttons.addWidget(resetButton)

    quitButton = QPushButton("&Quit")
    quitButton.clicked.connect(sys.exit)
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

  def compute(self):
    self.G.compute()

  
  def reset(self):
    self.G.reset()

    # load the graph with example data
    load_sha1_characteristic(self.G, "dc_char")
    #load_sha1_example_data(self.G)


if __name__ == "__main__":
  import sys
  from PyQt5.QtWidgets import QApplication

  app = QApplication(sys.argv)
  
  #g = SHA1FactorGraph(80, 4)
  #g = SHA1FactorGraph(64, 32)
  g = SHA1FactorGraph(80, 32)
  g.show()

  sys.exit(app.exec_()) 


