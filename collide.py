from hexdump import hexdump
import struct
from pprint import pprint
from characteristic import Characteristic

def bprint(x):
  return str(bin(x)[2:].rjust(32, '0'))


def ft(x,y,z,i):
  i /= 20
  if i == 0:
    return z ^ (x & (y ^ z))   # IF
  elif i == 2:
    return (x & y) | (x & z) | (y & z)   # MAJ
  elif i == 1 or i == 3:
    return x ^ y ^ z   # XOR

def ac(i):
  return [0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6][i/20]

def load_characteristics(name):
  a = []
  w = []
  for ln in open(name).read().split("\n"):
    lnn = ln.split(" ")
    if len(lnn) > 1:
      a.append(Characteristic(lnn[1]))
    if len(lnn) > 2:
      w.append(Characteristic(lnn[2]))
  return a,w

"""
A,W = load_characteristics("dc_char")

for i in range(-4, len(A)-4):
  print "%3d %32s " % (i, A[i+4], ),
  if i >= 0 and i < len(W):
    p1 = A[i+4] << 5 
    p2 = A[i] << 30
    p3 = W[i]
    p4 = ft(A[i+3], A[i+2] << 30, A[i+1] << 30, i)
    p5 = Characteristic(ac(i))

    out = Characteristic.add(p1,p2,p3,p4,p5)
    Pu = out.follows(A[i+5])

    print "%32s   %32s  %f" % (W[i], out, Pu)
  else:
    print ""
"""

def tonum(a, endian="big"):
  return list(struct.unpack(("!" if endian == "big" else "")+"I"*(len(a)/4), a))



def rl(a, i):
  return (a << i) & 0xFFFFFFFF | (a >> (32-i))

def rr(a, i):
  return rl(a, 32-i)

def xor(a, b):
  return [x^y for x,y in zip(a,b)]



def dump32(a):
  out = "%3d " % 0
  for i in range(0, len(a)):
    if (i % 4) == 0 and i != 0:
      out += "\n%3d " % i
    out += "%8.8X " % (a[i])
  print out



def expand(w, this_round=0, total_length=80):
  """SHA-1 expansion function from round this_round."""
  while len(w) < (this_round + 16):
    w = [rr(w[15], 1) ^ w[12] ^ w[7] ^ w[1]] + w

  while len(w) < total_length:
    w.append(rl(w[-3] ^ w[-8] ^ w[-14] ^ w[-16], 1))
  return w




def sha1(w, iv=None):
  """Compute SHA-1 over w and return q"""
  if iv == None:
    iv = tonum("67452301efcdab8998badcfe10325476c3d2e1f0".decode("hex"))
    q = [rr(iv[4], 30), rr(iv[3], 30), rr(iv[2], 30), iv[1], iv[0]]
  #iv = tonum("4633027d75b7a647d7e23d71915954dc3b81f936".decode("hex"))

  q = iv[:]

  #print "Q", q


  for t in range(0, 80):
    qt1 = ft(q[-2], rl(q[-3], 30), rl(q[-4], 30), t)
    """
    if t < 10:
      print hex(q[-2]), hex(rl(q[-3], 30)), hex(rl(q[-4], 30)), \
        "=", hex(qt1)
    """
    qt1 += ac(t)
    qt1 += w[t]
    qt1 += rl(q[-1], 5)
    qt1 += rl(q[-5], 30)
    q.append(qt1 & 0xFFFFFFFF)
  return q


def dv_to_differential(dv):
  """Expand a disturbance vector to a message differential"""
  dv = expand(dv[0:16], this_round=6, total_length=86)

  ret = [0]*(len(dv)+5)
  for i in range(len(dv)):
    ret[i+0] ^= dv[i]
    ret[i+1] ^= rl(dv[i], 5)
    ret[i+2] ^= dv[i]
    ret[i+3] ^= rl(dv[i], 30)
    ret[i+4] ^= rl(dv[i], 30)
    ret[i+5] ^= rl(dv[i], 30)
  return ret[6:86]

