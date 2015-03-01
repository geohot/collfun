# Unique Factors
#   f_if, f_maj, f_xor -- (4,4,4,4)         = 256
#   add_0, add_1       -- (25,25,4,4,4,4,4) = 640,000
#   xor5               -- (4,4,4,4,4)       = 1024

# b,c,d -> f
def f_if(b,c,d):
  return d ^ (b&(c^d))

# b,c,d -> f
def f_maj(b,c,d):
  return b&c ^ b&d ^ c&d

# b,c,d -> f
def f_xor(b,c,d):
  return b^c^d

# w, a, f, e, c_in -> c_out, o
def add_0(w, a, f, e):
  ret = w+a+f+e+0
  return (ret >> 1, ret & 1)
def addc_0(w, a, f, e, c_in):
  ret = c_in+w+a+f+e+0
  return (ret >> 1, ret & 1)

# w, a, f, e, c_in -> c_out, o
def add_1(w, a, f, e):
  ret = w+a+f+e+1
  return (ret >> 1, ret & 1)
def addc_1(w, a, f, e, c_in):
  ret = c_in+w+a+f+e+1
  return (ret >> 1, ret & 1)

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
  def __init__(self, dim):
    self.probs = [0.0]*dim
    self.dim = dim
    self.inFactors = []

  def fix(self, x):
    """Concentrate all probability in one place"""
    self.probs = [0.0]*self.dim
    self.probs[x] = 1.0

class Factor(object):
  def __init__(self, fxn, rvs):
    self.fxn = fxn
    self.rvs = rvs
    for rv in rvs:
      rv.inFactors.append(self)

# public class
class FactorGraph(object):
  def __init__(self):
    self.variables = {}
    self.factors = []

  def __getitem__(self, key):
    return self.variables[key]

  def addVariable(self, name, dim):
    self.variables[name] = Variable(dim)

  def addFactor(self, fxn, rvs):
    self.factors.append(Factor(fxn, map(lambda x: self.variables[x], rvs)))

def build_sha1_FactorGraph(rounds):
  G = FactorGraph()

  # add W's, F's, C's
  for i in range(rounds):
    for j in range(32):
      G.addVariable("W_%d_%d" % (i,j), 4)
      G.addVariable("F_%d_%d" % (i,j), 4)
    for j in range(31):
      G.addVariable("C_%d_%d" % (i,j), 25)

  # add A's
  for i in range(-4, rounds+1):
    for j in range(32):
      G.addVariable("A_%d_%d" % (i,j), 4)

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
        "A_%d_%d" % (i-2, (j+30) % 32),
        "A_%d_%d" % (i-3, (j+30) % 32),
        "F_%d_%d" % (i, j)])

  # add addition bullshit
  for i in range(rounds):
    k = [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]
    j = 0
    fxn = [add_0, add_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+5) % 32),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+30) % 32),
      "C_%d_%d" % (i, j),
      "A_%d_%d" % (i+1, j)])
    for j in range(1, 31):
      fxn = [addc_0, addc_1][(k>>j)&1]
      G.addFactor(fxn, [
        "W_%d_%d" % (i, j),
        "A_%d_%d" % (i-0, (j+5) % 32),
        "F_%d_%d" % (i, j),
        "A_%d_%d" % (i-4, (j+30) % 32),
        "C_%d_%d" % (i, j-1),
        "C_%d_%d" % (i, j),
        "A_%d_%d" % (i+1, j)])
    j = 31
    fxn = [add_0, add_1][(k>>j)&1]
    G.addFactor(fxn, [
      "W_%d_%d" % (i, j),
      "A_%d_%d" % (i-0, (j+5) % 32),
      "F_%d_%d" % (i, j),
      "A_%d_%d" % (i-4, (j+30) % 32),
      "C_%d_%d" % (i, j-1),
      "A_%d_%d" % (i+1, j)])

  return G
 
if __name__ == "__main__":
  G = build_sha1_FactorGraph(80)

  W_hello = [1751477356, 1870659584, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40]
  A_iv = [1732584193, 4023233417, 2562383102, 271733878, 3285377520]

  for i in range(len(W_hello)):
    for j in range(32):
      G["W_%d_%d" % (i,j)].fix( ((W_hello[i]>>j)&1) * 3)

  for i in range(len(A_iv)):
    for j in range(32):
      G["A_%d_%d" % (i-4,j)].fix( ((A_iv[i]>>j)&1) * 3)


