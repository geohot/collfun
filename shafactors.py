import time
from factorgraph import *

# Unique Factors
#   f_if, f_maj, f_xor -- (4,4,4,4)         = 256
#   add_0, add_1       -- (25,25,4,4,4,4,4) = 640,000
#   xor5               -- (4,4,4,4,4)       = 1024

start = time.time()

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_if(d,c,b):
  return d ^ (b & (c ^ d))

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_maj(d,c,b):
  return b&c ^ b&d ^ c&d

# b,c,d -> f
@factor([2,2,2], 2, True)
def f_xor(d,c,b):
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

@factor([4,4], 2)
def equal(x1, x2):
  return x1 == x2

print "built factor matrices in %f s" % (time.time()-start)

# Bit Random Variables
#   W_(0,79)_(0,31)   -- 80*32 --  4 states
#   A_(-4, 80)_(0,31) -- 85*32 --  4 states
#   F_(0,79)_(0,31)   -- 80*32 --  4 states
#   C_(0,79)_(0,30)   -- 80*31 -- 25 states

def add_sha1_factors_for_round(G, i, bits=32):
  fxn = [f_if, f_xor, f_maj, f_xor][i/20]
  k = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]

  for j in range(bits):
    G.addFactor(fxn, [
      "A_%d_%d" % (i-3, (j+2) % bits),
      "A_%d_%d" % (i-2, (j+2) % bits),
      "A_%d_%d" % (i-1, j),
      "F_%d_%d" % (i, j)])

  j = 0
  fxn = [add_0, add_1][(k>>j)&1]
  G.addFactor(fxn, [
    "A_%d_%d" % (i-4, (j+2) % bits),
    "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
    "F_%d_%d" % (i, j),
    "W_%d_%d" % (i, j),
    "A_%d_%d" % (i+1, j)])
  fxn = [carry_0, carry_1][(k>>j)&1]
  G.addFactor(fxn, [
    "A_%d_%d" % (i-4, (j+2) % bits),
    "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
    "F_%d_%d" % (i, j),
    "W_%d_%d" % (i, j),
    "C_%d_%d" % (i, j)])
  for j in range(1, bits):
    fxn = [addc_0, addc_1][(k>>j)&1]
    G.addFactor(fxn, [
      "A_%d_%d" % (i-4, (j+2) % bits),
      "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
      "F_%d_%d" % (i, j),
      "W_%d_%d" % (i, j),
      "C_%d_%d" % (i, j-1),
      "A_%d_%d" % (i+1, j)])
    if j != bits-1:
      fxn = [carryc_0, carryc_1][(k>>j)&1]
      G.addFactor(fxn, [
        "A_%d_%d" % (i-4, (j+2) % bits),
        "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
        "F_%d_%d" % (i, j),
        "W_%d_%d" % (i, j),
        "C_%d_%d" % (i, j-1),
        "C_%d_%d" % (i, j)])

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
  # add addition bullshit
  for i in range(rounds):
    add_sha1_factors_for_round(G, i)

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

