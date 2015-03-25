import time
from factorgraph import *

# *** null factor ***

@factor([], 2)
def zero():
  return 0

# *** boolean function factors ***

# b,c,d -> f
@factor([2,2,2], 2)
def f_if(d,c,b):
  return d ^ (b & (c ^ d))

# b,c,d -> f
@factor([2,2,2], 2)
def f_maj(d,c,b):
  return b&c ^ b&d ^ c&d

# b,c,d -> f
@factor([2,2,2], 2)
def f_xor(d,c,b):
  return b^c^d

# *** expansion factor ***

@factor([2,2,2,2], 2)
def xor5(x1, x2, x3, x4):
  return x1 ^ x2 ^ x3 ^ x4


# *** addition factors ***

@factor([2,2,2,2,2,2], 2)
def add_0_c0(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+0)>>0) & 1

@factor([2,2,2,2,2,2], 2)
def add_0_c1(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+0)>>1) & 1

@factor([2,2,2,2,2,2], 2)
def add_0_c2(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+0)>>2) & 1

add_0 = [add_0_c0, add_0_c1, add_0_c2]


@factor([2,2,2,2,2,2], 2)
def add_1_c0(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+1)>>0) & 1

@factor([2,2,2,2,2,2], 2)
def add_1_c1(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+1)>>1) & 1

@factor([2,2,2,2,2,2], 2)
def add_1_c2(w, a, f, e, c0, c1):
  return ((w+a+f+e+c0+c1+1)>>2) & 1

add_1 = [add_1_c0, add_1_c1, add_1_c2]

# *** functions to set up factors ***

def add_sha1_factors_for_round(G, i, bits=32):
  fxn = [f_if, f_xor, f_maj, f_xor][i/20]
  k = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]

  for j in range(bits):
    G.addFactor(fxn, [
      "A_%d_%d" % (i-3, (j+2) % bits),
      "A_%d_%d" % (i-2, (j+2) % bits),
      "A_%d_%d" % (i-1, j),
      "F_%d_%d" % (i, j)])

  for j in range(0, bits):
    fxn = [add_0, add_1][(k>>j)&1]
    if j == 0:
      C1 = "zero"
      C2 = "zero"
    elif j == 1:
      C1 = "C1_%d_%d" % (i, j-1)
      C2 = "zero"
    else:
      C1 = "C1_%d_%d" % (i, j-1)
      C2 = "C2_%d_%d" % (i, j-2)

    G.addFactor(fxn[0], [
      "A_%d_%d" % (i-4, (j+2) % bits),
      "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
      "F_%d_%d" % (i, j),
      "W_%d_%d" % (i, j),
      C1, C2,
      "A_%d_%d" % (i+1, j)])

    if j < bits-1:
      G.addFactor(fxn[1], [
        "A_%d_%d" % (i-4, (j+2) % bits),
        "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
        "F_%d_%d" % (i, j),
        "W_%d_%d" % (i, j),
        C1, C2,
        "C1_%d_%d" % (i, j)])

    if j < bits-2:
      G.addFactor(fxn[2], [
        "A_%d_%d" % (i-4, (j+2) % bits),
        "A_%d_%d" % (i-0, (j+(bits-5)) % bits),
        "F_%d_%d" % (i, j),
        "W_%d_%d" % (i, j),
        C1, C2,
        "C2_%d_%d" % (i, j)])
      
def build_sha1_FactorGraph(rounds, bits):
  G = FactorGraph()

  # zero factor
  G.addVariable("zero", 2)
  G.addFactor(zero, ["zero"])

  # add W's, F's, C's
  for i in range(rounds):
    FactorByte(G, "W_%d" % i, 2, bits)
    FactorByte(G, "F_%d" % i, 2, bits)
    FactorByte(G, "C1_%d" % i, 2, bits-1)
    FactorByte(G, "C2_%d" % i, 2, bits-2)

  A = [FactorByte(G, "A_%d" % i, 2, bits) for i in range(-4, rounds+1)]

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
    add_sha1_factors_for_round(G, i, bits)

  return G

W_hello = [1751477356, 1870659584, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40]
A_iv = [256608195, 1086935512, 1659597818, 4023233417, 1732584193]

def load_sha1_example_data(G):
  for i in range(len(W_hello)):
    for j in range(32):
      try:
        G["W_%d_%d" % (i,j)].fix( ((W_hello[i]>>j)&1) )
      except:
        pass

  for i in range(len(A_iv)):
    for j in range(32):
      try:
        G["A_%d_%d" % (i-4,j)].fix( ((A_iv[i]>>j)&1) )
      except:
        pass

def dump(G, name = "A", start = -4, end = 81):
  out = [''.join([str(G["%s_%d_%d" % (name, i, j)]) for j in range(31,-1,-1)]) for i in range(start, end)]
  return map(lambda x: int(x, 2), out)

if __name__ == "__main__":
  G = build_sha1_FactorGraph(80, 32)

  G.reset()
  load_sha1_example_data(G)
  G.compute()

  import collide
  tW = collide.expand(W_hello)
  tA = collide.sha1(tW, A_iv)

  assert tW == dump(G, "W", 0, 80)
  assert tA == dump(G, "A", -4, 81)

  print "tests pass"


