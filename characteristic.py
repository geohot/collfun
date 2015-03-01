from collections import defaultdict
from math import log

class Bit(object):
  """Bit is a Random Variable over [(0,0), (0,1), (1,0), (1,1)]"""

  BITPATTERNS = [(0,0),(0,1),(1,0),(1,1)]
  BITPATTERNS_IDX = zip(range(len(BITPATTERNS)), BITPATTERNS)

  # uniform prior
  # could use fractions here instead of floats
  CONDITIONS = {
    '?': [0.25, 0.25, 0.25, 0.25],
    'x': [0.00, 0.50, 0.50, 0.00],
    '-': [0.50, 0.00, 0.00, 0.50],

    '0': [1.00, 0.00, 0.00, 0.00],
    'n': [0.00, 1.00, 0.00, 0.00],
    'u': [0.00, 0.00, 1.00, 0.00],
    '1': [0.00, 0.00, 0.00, 1.00],

    '3': [0.50, 0.50, 0.00, 0.00],
    '5': [0.50, 0.00, 0.50, 0.00],
    '7': [1/3., 1/3., 1/3., 0.00],
    'A': [0.00, 0.50, 0.00, 0.50],
    'B': [1/3., 1/3., 0.00, 1/3.],
    'C': [0.00, 0.00, 0.50, 0.50],
    'D': [1/3., 0.00, 1/3., 1/3.],
    'E': [0.00, 1/3., 1/3., 1/3.],
    }

  def __init__(self, c):
    if type(c) is str:
      self.prob = self.CONDITIONS[c]
    else:
      # must be normalized
      #assert sum(c) == 1.00
      self.prob = c

  def __str__(self):
    for c in self.CONDITIONS:
      if self.CONDITIONS[c] == self.prob:
        return c
    return '!'
        
  # bit level ops
  def bitops(self, rhs, fxn):
    """Takes in two length 4 probability vectors
       self.prob and rhs.prob
       And applies fxn to them"""

    ret = [0.00]*4
    for x, X in self.BITPATTERNS_IDX:
      for y, Y in self.BITPATTERNS_IDX:
        key = self.BITPATTERNS.index((fxn(X[0], Y[0]), fxn(X[1], Y[1])))
        ret[key] += self.prob[x] * rhs.prob[y]
    # should be normalized
    return Bit(ret)

  def __and__(self, rhs):
    return self.bitops(rhs, lambda x,y: x&y)
  def __or__(self, rhs):
    return self.bitops(rhs, lambda x,y: x|y)
  def __xor__(self, rhs):
    return self.bitops(rhs, lambda x,y: x^y)

  def add(*args):
    """Add a list of bits, output a dictionary of probabilities"""
    acc = {(0,0): 1.00}
    for bit in args:
      nacc = defaultdict(float)
      for k in acc:
        for x, X in Bit.BITPATTERNS_IDX:
          if bit.prob[x] > 0:
            nacc[(k[0] + X[0], k[1] + X[1])] += bit.prob[x] * acc[k]
      acc = nacc
    return acc


class Characteristic(object):
  def __init__(self, x):
    if type(x) is list:
      assert len(x) == 32
      self.bits = x
    elif type(x) is str:
      assert len(x) == 32
      self.bits = map(lambda x: Bit(x), list(x)[::-1])
    else:
      self.bits = []
      for i in range(32):
        if (x>>i)&1:
          self.bits.append(Bit('1'))
        else:
          self.bits.append(Bit('0'))

  def __str__(self):
    return ''.join(map(str, self.bits))[::-1]

  # rotations happen at the byte level
  def __rshift__(self, num):
    return Characteristic(self.bits[num:]+self.bits[0:num])
  def __lshift__(self, num):
    return self >> (32-num)

  # addition is hard, and happens at the byte level
  def add(*args):
    """Add a list of words, output a Characteristic of the added words. Handle carries."""
    ret = []
    # loop over bits
    # this is wrong because both carries depend on each other 
    carry = {(0,0): 1.0}
    for i in range(32):
      # loop over each bit we add
      bits = map(lambda x: x.bits[i], args)
      tb = Bit.add(*bits)
      tbn = defaultdict(float)

      # add in the old carry
      for k in tb:
        for c in carry:
          tbn[(k[0] + c[0], k[1] + c[1])] += tb[k] * carry[c]

      # tb can be expanded into, this_bit, carry, and double_carry
      ncarry = defaultdict(float)  # replace with SparseBit?
      t0 = [0.0]*4
      print tbn
      for k in tbn:
        t0[Bit.BITPATTERNS.index((k[0]&1, k[1]&1))] += tbn[k]
        ncarry[(k[0]>>1, k[1]>>1)] += tbn[k]

      #print tbn, t0
      ret.append(Bit(t0))
      carry = ncarry
    return Characteristic(ret)

  # and, or, xor happen at the bit level
  def __and__(self, rhs):
    return Characteristic( [x[0] & x[1] for x in zip(self.bits, rhs.bits)] )
  def __or__(self, rhs):
    return Characteristic( [x[0] | x[1] for x in zip(self.bits, rhs.bits)] )
  def __xor__(self, rhs):
    return Characteristic( [x[0] ^ x[1] for x in zip(self.bits, rhs.bits)] )

  def follows(self, th):
    """Log odds follows"""
    ret = 0
    for i in range(32):
      prob = 0.0
      for k in range(4):
        if th.bits[i].prob[k] > 0.0:
          prob += self.bits[i].prob[k]
      ret += log(prob, 2)
    return ret

