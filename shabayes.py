import sys
import numpy as np
import itertools
import logging
import flask

log = logging.getLogger('MyLogger')
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stderr))

# Unique Factors
#   f_if, f_maj, f_xor -- (4,4,4,4)         = 256
#   add_0, add_1       -- (25,25,4,4,4,4,4) = 640,000
#   xor5               -- (4,4,4,4,4)       = 1024

# b,c,d -> f
def f_if(b,c,d):
  return d ^ (b & (c ^ d))

# b,c,d -> f
def f_maj(b,c,d):
  return b&c ^ b&d ^ c&d

# b,c,d -> f
def f_xor(b,c,d):
  return b^c^d

# w, a, f, e, c_in -> c_out, o
def add_0(w, a, f, e):
  return (w+a+f+e+0) & 1
def addc_0(w, a, f, e, c_in):
  return (w+a+f+e+c_in+0) & 1
def carry_0(w, a, f, e):
  return (w+a+f+e+0) >> 1
def carryc_0(w, a, f, e, c_in):
  return (w+a+f+e+c_in+0) >> 1

# w, a, f, e, c_in -> c_out, o
def add_1(w, a, f, e):
  return (w+a+f+e+1) & 1
def addc_1(w, a, f, e, c_in):
  return (w+a+f+e+c_in+1) & 1
def carry_1(w, a, f, e):
  return (w+a+f+e+1) >> 1
def carryc_1(w, a, f, e, c_in):
  return (w+a+f+e+c_in+1) >> 1

# x1, x2, x3, x4 -> x5
def xor5(x1, x2, x3, x4):
  return x1 ^ x2 ^ x3 ^ x4

# Bit Random Variables
#   W_(0,79)_(0,31)   -- 80*32 --  4 states
#   A_(-4, 80)_(0,31) -- 85*32 --  4 states
#   F_(0,79)_(0,31)   -- 80*32 --  4 states
#   C_(0,79)_(0,30)   -- 80*31 -- 25 states

# classes are private to FactorGraph
class Variable(object):
  def __init__(self, name, dim):
    self.probs = None
    self.name = name
    self.dim = dim
    self.qt = None
    self.inFactors = []

  def __str__(self):
    if self.probs == [0.0, 1.0]:
      return '1'
    elif self.probs == [1.0, 0.0]:
      return '0'
    return '?'

  def setProbs(self, p):
    self.probs = p
    if self.qt != None:
      self.qt.setText(str(self))

  def fix(self, x):
    """Concentrate all probability in one place"""
    probs = [0.0]*self.dim
    probs[x] = 1.0
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
      self.variables[k].probs = None

  def compute(self):
    did_compute = True
    rounds = 0
    var = 0
    while did_compute:
      rounds += 1
      did_compute = False
      for f in self.factors:
        if f.compute():
          var += 1
          did_compute = True
    log.debug("%d variables computed in %d rounds" % (var, rounds))

  def addVariable(self, name, dim):
    self.variables[name] = Variable(name, dim)

  def addFactor(self, fxn, rvs):
    rvs = map(lambda x: self.variables[x], rvs)
    name = fxn.func_name
    if name not in self.mats:
      dims = map(lambda x: x.dim, rvs)
      matrix = np.zeros(dims)
      ins = fxn.func_code.co_argcount
      for sins in itertools.product(*map(range, dims[0:ins])):
        matrix[sins+(fxn(*sins),)] = 1.0
      self.mats[name] = matrix

      #print "%8s %3d %3d" % (name, np.product(dims[0:ins]), np.product(dims)), dims[0:ins], dims[ins:]

    self.factors.append(Factor(self.mats[name], rvs))

def build_sha1_FactorGraph(rounds):
  G = FactorGraph()

  # add W's, F's, C's
  for i in range(rounds):
    for j in range(32):
      G.addVariable("W_%d_%d" % (i,j), 2)
      G.addVariable("F_%d_%d" % (i,j), 2)
    for j in range(31):
      G.addVariable("C_%d_%d" % (i,j), 5)

  # add A's
  for i in range(-4, rounds+1):
    for j in range(32):
      G.addVariable("A_%d_%d" % (i,j), 2)

  # add linear W factors
  for i in range(16, rounds):
    for j in range(32):
      G.addFactor(xor5, [
        "W_%d_%d" % (i-16, j),
        "W_%d_%d" % (i-14, j),
        "W_%d_%d" % (i-8, j),
        "W_%d_%d" % (i-3, j),
        "W_%d_%d" % (i, (j+1) % 32)])

  # add boolean F factors
  for i in range(rounds):
    fxn = [f_if, f_xor, f_maj, f_xor][i/20]
    for j in range(32):
      G.addFactor(fxn, [
        "A_%d_%d" % (i-1, j),
        "A_%d_%d" % (i-2, (j+2) % 32),
        "A_%d_%d" % (i-3, (j+2) % 32),
        "F_%d_%d" % (i, j)])

  # add addition bullshit
  for i in range(rounds):
    k = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]
    j = 0
    fxn = [add_0, add_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+(32-5)) % 32),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+2) % 32),
      "A_%d_%d" % (i+1, j)])
    fxn = [carry_0, carry_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+(32-5)) % 32),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+2) % 32),
      "C_%d_%d" % (i, j)])
    for j in range(1, 32):
      fxn = [addc_0, addc_1][(k>>j)&1]
      G.addFactor(fxn, [
        "W_%d_%d" % (i, j),
        "A_%d_%d" % (i-0, (j+(32-5)) % 32),
        "F_%d_%d" % (i, j),
        "A_%d_%d" % (i-4, (j+2) % 32),
        "C_%d_%d" % (i, j-1),
        "A_%d_%d" % (i+1, j)])
      if j != 31:
        fxn = [carryc_0, carryc_1][(k>>j)&1]
        G.addFactor(fxn, [
          "W_%d_%d" % (i, j),
          "A_%d_%d" % (i-0, (j+(32-5)) % 32),
          "F_%d_%d" % (i, j),
          "A_%d_%d" % (i-4, (j+2) % 32),
          "C_%d_%d" % (i, j-1),
          "C_%d_%d" % (i, j)])

  return G


def load_sha1_example_data(G):
  W_hello = [1751477356, 1870659584, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40]
  A_iv = [256608195, 1086935512, 1659597818, 4023233417, 1732584193]

  for i in range(len(W_hello)):
    for j in range(32):
      G["W_%d_%d" % (i,j)].fix( ((W_hello[i]>>j)&1) )

  for i in range(len(A_iv)):
    for j in range(32):
      G["A_%d_%d" % (i-4,j)].fix( ((A_iv[i]>>j)&1) )


from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget)

class SHA1FactorGraph(QWidget):
  def __init__(self, parent=None):
    super(SHA1FactorGraph, self).__init__(parent)

    # construct the graph
    self.rounds = 80
    self.G = build_sha1_FactorGraph(self.rounds)

    # display the Ws
    WLayout = QGridLayout()
    WLayout.setSpacing(0)
    for i in range(0,4):
      WLayout.addWidget(QLabel(""), i, 0)
    WLayout.addWidget(QLabel(""), self.rounds+4, 0)

    for i in range(self.rounds):
      for j in range(32):
        widget = QLabel("#")
        self.G["W_%d_%d" % (i,j)].qt = widget
        WLayout.addWidget(widget, i+4, j)

    # display the As
    ALayout = QGridLayout()
    ALayout.setSpacing(0)
    for i in range(-4, self.rounds+1):
      for j in range(32):
        widget = QLabel("#")
        self.G["A_%d_%d" % (i,j)].qt = widget
        ALayout.addWidget(widget, i+4, j)

    Buttons = QVBoxLayout()

    computeButton = QPushButton("&Compute")
    computeButton.clicked.connect(self.compute)
    Buttons.addWidget(computeButton)

    quitButton = QPushButton("&Quit")
    quitButton.clicked.connect(sys.exit)
    Buttons.addWidget(quitButton)

    mainLayout = QHBoxLayout()
    mainLayout.addLayout(WLayout)
    mainLayout.addLayout(ALayout)
    mainLayout.addLayout(Buttons)

    # load the graph with example data
    load_sha1_example_data(self.G)

    self.setLayout(mainLayout)
    self.setWindowTitle("SHA1 Factor Graph")

  def compute(self):
    self.G.compute()



 
if __name__ == "__main__":
  import sys
  from PyQt5.QtWidgets import QApplication

  app = QApplication(sys.argv)
  
  g = SHA1FactorGraph()
  g.show()

  sys.exit(app.exec_()) 

"""
  ROUNDS = 80
  G = build_sha1_FactorGraph(ROUNDS)

  exit(0)


  G.compute()

  outt = []
  for i in range(ROUNDS):
    out = 0
    for j in range(32):
      var = G["W_%d_%d" % (i,j)]
      out |= np.argmax(var.probs)<<j
    outt.append(out)
  print map(hex, outt)

  outt = []
  for i in range(-4, ROUNDS+1):
    out = 0
    for j in range(32):
      var = G["A_%d_%d" % (i,j)]
      out |= np.argmax(var.probs)<<j
    outt.append(out)
  print map(hex, outt)

  #print hex(out + A_iv[0])
"""

