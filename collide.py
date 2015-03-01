from hexdump import hexdump
import struct
from pprint import pprint
from characteristic import Characteristic

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


exit(0)


def rl(a, i):
  return (a << i) & 0xFFFFFFFF | (a >> (32-i))

def rr(a, i):
  return rl(a, 32-i)

def xor(a, b):
  return [x^y for x,y in zip(a,b)]

def tonum(a, endian="big"):
  return list(struct.unpack(("!" if endian == "big" else "")+"I"*(len(a)/4), a))


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

def sha1(w):
  """Compute SHA-1 over w and return q"""
  #iv = tonum("67452301efcdab8998badcfe10325476c3d2e1f0".decode("hex"))
  iv = tonum("4633027d75b7a647d7e23d71915954dc3b81f936".decode("hex"))
  q = [rr(iv[4], 30), rr(iv[3], 30), rr(iv[2], 30), iv[1], iv[0]]

  for t in range(0, 80):
    qt1 = ft(q[-2], rl(q[-3], 30), rl(q[-4], 30), t)
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
    

dv = expand([0,0,0,0,0x80000000,0,0,0,0,0,0x80000000,0,0x80000000,0,0,0], 43)
diff = dv_to_differential(dv)

"""
for i in range(len(dv)):
  print "%3d %s" % (i, bprint(dv[i]))
"""

#print len(dv)




m1 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 73 e6 e2 c8 43 7f b1 3e 4e 4d 5d b6 e3 83 e0 1d 7b ea 24 2c 2b b6 30 54 68 45 b1 43 0c 21 94 ab fb 52 36 be 2b c9 1e 19 1d 11 bf 8f 66 5e f9 ab 9f 8f e3 6a 40 2c bf 39 d7 7c 1f b4 3c b0 08 72".replace(" ", "").decode("hex"))
m2 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 7f e6 e2 ca 83 7f b1 2e fa 4d 5d aa df 83 e0 19 c7 ea 24 36 0b b6 30 44 4c 45 b1 5f e0 21 94 bf f7 52 36 bc eb c9 1e 09 a9 11 bf 93 4a 5e f9 af 23 8f e3 72 f0 2c bf 29 d7 7c 1f b8 84 b0 08 62".replace(" ", "").decode("hex"))

w = tonum("hello\x80" + "\x00"*(56 - 6) + struct.pack("!Q", 8*5))
#q = sha1(expand(w))
#print m1[0:16] == m2[0:16]

mm1 = sha1(expand(m1[16:32]))
mm2 = sha1(expand(m2[16:32]))
#w = xor(expand(m1[16:32]), expand(m2[16:32]))
a = xor(mm1, mm2)

#print mm1
#print mm2

#dump32(xor(mm1, mm2))

for i in range(-5, 80):
  print "%3d %32s %32s" % (i,
    Characteristic(a[i+5]),
    Characteristic(diff[i]) if i >= 0 else "",
    )
    #Characteristic(dv[i]) if i >= 0 else "",
    #bprint(w[i]) if i >= 0 else "",





"""
dump32(w)
print "Q"
dump32(q)

out = []
for i in range(0, 5):
  rotate = 0 if i < 2 else 30
  out.append((rl(q[4-i], rotate) + rl(q[-1-i], rotate)) & 0xFFFFFFFF)

print map(hex, out)
"""



