from hexdump import hexdump
import struct

def rl(a, i):
  return (a << i) & 0xFFFFFFFF | (a >> (32-i))

def rr(a, i):
  return rl(a, 32-i)

def tonum(a, endian="big"):
  return list(struct.unpack(("!" if endian == "big" else "")+"I"*(len(a)/4), a))

def dump32(a):
  out = "%3d " % 0
  for i in range(0, len(a)):
    if (i % 4) == 0 and i != 0:
      out += "\n%3d " % i
    out += "%8.8X " % (a[i])
  print out
    

def ft(x,y,z,i):
  i /= 20
  if i == 0:
    return z ^ (x & (y ^ z))
  elif i == 1 or i == 3:
    return x ^ y ^ z
  elif i == 2:
    return (x & y) | (x & z) | (y & z)

def ac(i):
  i /= 20
  if i == 0:
    return 0x5a827999
  elif i == 1:
    return 0x6ed9eba1
  elif i == 2:
    return 0x8f1bbcdc
  elif i == 3:
    return 0xca62c1d6

def bprint(a):
  out = []
  for i in range(32):
    if a & 0x80000000:
      out.append('o')
    else:
      out.append('-')
    a <<= 1
  return ''.join(out)

def expand(w, this_round=0):
  """SHA-1 expansion function from round this_round."""
  while len(w) < (this_round + 16):
    w = [rr(w[15], 1) ^ w[12] ^ w[7] ^ w[1]] + w

  while len(w) < 80:
    w.append(rl(w[-3] ^ w[-8] ^ w[-14] ^ w[-16], 1))
  return w

dv = expand([0,0,0,0,0x80000000,0,0,0,0,0,0x80000000,0,0x80000000,0,0,0], 44)

"""
for i in range(len(dv)):
  print "%3d %s" % (i, bprint(dv[i]))
"""

#print len(dv)

iv = tonum("67452301efcdab8998badcfe10325476c3d2e1f0".decode("hex"))
q = [rr(iv[4], 30), rr(iv[3], 30), rr(iv[2], 30), iv[1], iv[0]]


m1 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 73 e6 e2 c8 43 7f b1 3e 4e 4d 5d b6 e3 83 e0 1d 7b ea 24 2c 2b b6 30 54 68 45 b1 43 0c 21 94 ab fb 52 36 be 2b c9 1e 19 1d 11 bf 8f 66 5e f9 ab 9f 8f e3 6a 40 2c bf 39 d7 7c 1f b4 3c b0 08 72".replace(" ", "").decode("hex"))
m2 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 7f e6 e2 ca 83 7f b1 2e fa 4d 5d aa df 83 e0 19 c7 ea 24 36 0b b6 30 44 4c 45 b1 5f e0 21 94 bf f7 52 36 bc eb c9 1e 09 a9 11 bf 93 4a 5e f9 af 23 8f e3 72 f0 2c bf 29 d7 7c 1f b8 84 b0 08 62".replace(" ", "").decode("hex"))

w = tonum("hello\x80" + "\x00"*(56 - 6) + struct.pack("!Q", 8*5))
w = expand(w)

for t in range(0, 80):
  qt1 = ft(q[-2], rl(q[-3], 30), rl(q[-4], 30), t)
  qt1 += ac(t)
  qt1 += w[t]
  qt1 += rl(q[-1], 5)
  qt1 += rl(q[-5], 30)
  q.append(qt1 & 0xFFFFFFFF)

dump32(w)

print "Q"
dump32(q)

print "out:",hex((q[4] + q[-1]) & 0xFFFFFFFF)



